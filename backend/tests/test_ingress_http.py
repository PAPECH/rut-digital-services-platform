from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.support_chat.presentation import messages_router as messages_module
from app.db.session import get_db
from app.models.enums import MessageDirectionEnum, SystemEnum
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.consent.infrastructure.models import UserConsentRecord
from app.modules.knowledge_base.domain.entities import MatchResult, MatchTier
from app.modules.profiles.domain.entities import BotMembership
from app.modules.profiles.infrastructure.models import User
from app.modules.support_chat.infrastructure.models import Message
from app.modules.tenancy.presentation.dependencies import resolve_tenant


def _active_consent() -> UserConsentRecord:
    """Default for tests that aren't about the consent gate itself -- Task 064's gate now
    sits in front of /messages/ingress too, so every pre-existing test needs a consent
    query answered, not just the User query it originally exercised."""
    return UserConsentRecord(
        id=1,
        external_user_id="max-1",
        system=SystemEnum.max,
        given_at=datetime(2026, 1, 1, tzinfo=UTC),
        revoked_at=None,
        deletion_due_at=None,
        deleted_at=None,
        policy_version="v1",
    )


class _Scalar:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    """Как _FakeSession в test_ai_callback_http.py, но для /messages/ingress:
    поддерживает только User-запрос (внешний id найден сразу, ветка создания
    нового пользователя не нужна для этих тестов) и учёт add/flush/commit, чтобы
    проверить, что именно было записано."""

    def __init__(
        self,
        *,
        user: User | None = None,
        deny_all: bool = False,
        consent: UserConsentRecord | None = "__default_active__",
    ) -> None:
        self._user = user
        self._deny_all = deny_all
        self._consent = _active_consent() if consent == "__default_active__" else consent
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0
        self._next_id = 1000

    def _deny(self) -> None:
        if self._deny_all:
            raise AssertionError("no DB access expected when chat is disabled")

    def execute(self, stmt):
        self._deny()
        entity = stmt.column_descriptions[0]["entity"]
        if entity is User:
            return _Scalar(self._user)
        if entity is UserConsentRecord:
            return _Scalar(self._consent)
        raise AssertionError(f"unexpected query entity: {entity}")

    def add(self, obj) -> None:
        self._deny()
        self.added.append(obj)

    def flush(self) -> None:
        self._deny()
        self.flushes += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    def commit(self) -> None:
        self._deny()
        self.commits += 1

    def refresh(self, obj) -> None:
        self._deny()
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(UTC)
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = datetime.now(UTC)


class _FakeEnsureBotMembership:
    """Обходит SqlAlchemyProfileGateway целиком — членство/баны не то, что эти
    тесты проверяют, а конструктор реального гейтвея не должен трогать fake-сессию."""

    def __init__(self, _gateway) -> None:
        pass

    def execute(self, bot_instance_id: int, user_id: int) -> BotMembership:
        return BotMembership(id=1, bot_instance_id=bot_instance_id, user_id=user_id)


def _app(bot: BotInstance, session: _FakeSession) -> FastAPI:
    app = FastAPI()
    app.include_router(messages_module.router, prefix="/messages")
    app.dependency_overrides[resolve_tenant] = lambda: bot
    app.dependency_overrides[get_db] = lambda: session
    return app


class _FakeMatchKnowledgeBase:
    """Заменяет messages_module.MatchKnowledgeBase — репозиторий/эмбеддер всё равно
    конструируются с fake-сессией, но никогда не используются по-настоящему."""

    _result: MatchResult = MatchResult(MatchTier.SKIP)

    def __init__(self, _repository, _embedder) -> None:
        pass

    def execute(self, *_a, **_k):
        return self._result


def _fake_match_knowledge_base(monkeypatch, *, result: MatchResult) -> None:
    fake = type("_FakeMatchKnowledgeBase", (_FakeMatchKnowledgeBase,), {"_result": result})
    monkeypatch.setattr(messages_module, "MatchKnowledgeBase", fake)


def _patch_common(monkeypatch) -> None:
    monkeypatch.setattr(messages_module, "authorize_bot_runtime", lambda *_a, **_k: None)
    monkeypatch.setattr(messages_module, "EnsureBotMembership", _FakeEnsureBotMembership)


def _user() -> User:
    return User(id=17, user_id="123456", system=SystemEnum.max, language_code="ru")


def test_chat_disabled_short_circuits_before_any_db_access(monkeypatch) -> None:
    bot = BotInstance(
        id=1,
        slug="bot-1",
        name="Информационный бот",
        settings={"chat": {"student_text_enabled": False}},
    )
    session = _FakeSession(deny_all=True)
    _patch_common(monkeypatch)

    class _FailIfConstructed:
        def __init__(self, *_a, **_k) -> None:
            raise AssertionError("MatchKnowledgeBase must not run when chat is disabled")

    monkeypatch.setattr(messages_module, "MatchKnowledgeBase", _FailIfConstructed)
    app = _app(bot, session)

    response = TestClient(app).post(
        "/messages/ingress",
        json={"user_id": "123456", "system": "max", "text": "Позовите оператора"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_disabled"] is True
    assert body["message"] is None
    assert session.commits == 0
    assert session.added == []


def test_chat_enabled_by_default_when_setting_unset(monkeypatch) -> None:
    # No "chat" key at all in settings -- must behave exactly as before this task.
    bot = BotInstance(id=1, slug="bot-1", name="Бот", settings={})
    session = _FakeSession(user=_user())
    _patch_common(monkeypatch)
    _fake_match_knowledge_base(monkeypatch, result=MatchResult(MatchTier.SKIP))
    app = _app(bot, session)

    response = TestClient(app).post(
        "/messages/ingress",
        json={"user_id": "123456", "system": "max", "text": "привет"},
    )

    assert response.status_code == 200
    assert response.json()["chat_disabled"] is False
    # SKIP tier still persists the incoming message and falls into the staff queue.
    assert len(session.added) == 1


def test_escalate_via_free_text_persists_only_incoming_message(monkeypatch) -> None:
    """Регрессия для Task 049: раньше эскалация текстом писала исходящее
    подтверждение сразу за входящим, из-за чего has_open_ticket (чисто по
    timestamp'ам, tickets.py) считал тикет уже закрытым. Теперь исходящее не
    создаётся вообще -- только входящее сообщение студента."""
    bot = BotInstance(id=1, slug="bot-1", name="Бот", settings={})
    session = _FakeSession(user=_user())
    _patch_common(monkeypatch)
    _fake_match_knowledge_base(monkeypatch, result=MatchResult(MatchTier.ESCALATE))
    app = _app(bot, session)

    response = TestClient(app).post(
        "/messages/ingress",
        json={"user_id": "123456", "system": "max", "text": "позовите оператора пожалуйста"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is not None and "поддержки" in body["answer"]

    assert len(session.added) == 1
    only_message = session.added[0]
    assert isinstance(only_message, Message)
    assert only_message.direction == MessageDirectionEnum.in_
    assert only_message.ai_classification == "kb_staff_requested_text"
