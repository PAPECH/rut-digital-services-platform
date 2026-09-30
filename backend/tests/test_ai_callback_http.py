from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.support_chat.presentation import messages_router as messages_module
from app.db.session import get_db
from app.models.enums import MessageDirectionEnum, SystemEnum
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.knowledge_base.infrastructure.models import KbDocumentRecord
from app.modules.profiles.infrastructure.models import User
from app.modules.support_chat.infrastructure.models import Message
from app.modules.tenancy.presentation.dependencies import resolve_tenant


class _Scalar:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, *, user=None, incoming=None, document=None) -> None:
        self._user = user
        self._incoming = incoming
        self._document = document
        self.added: list[object] = []
        self.commits = 0
        self._next_id = 1000

    def execute(self, stmt):
        entity = stmt.column_descriptions[0]["entity"]
        if entity is User:
            return _Scalar(self._user)
        if entity is Message:
            return _Scalar(self._incoming)
        if entity is KbDocumentRecord:
            return _Scalar(self._document)
        raise AssertionError(f"unexpected query entity: {entity}")

    def add(self, obj) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        # В реальной сессии flush/commit проставляет PK и timestamp-дефолты —
        # здесь эмулируем то же самое, иначе MessageOut.model_validate упадёт.
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(UTC)
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = datetime.now(UTC)


def _app(bot_id: int, session: _FakeSession) -> FastAPI:
    app = FastAPI()
    app.include_router(messages_module.router, prefix="/messages")
    app.dependency_overrides[resolve_tenant] = lambda: BotInstance(
        id=bot_id, slug=f"bot-{bot_id}", name="Бот"
    )
    app.dependency_overrides[get_db] = lambda: session
    return app


def _patch_common(monkeypatch, *, redis_claims: bool = True) -> None:
    monkeypatch.setattr(messages_module, "authorize_bot_runtime", lambda *_a, **_k: None)
    monkeypatch.setattr(
        messages_module.redis_client,
        "set",
        lambda *_a, **_k: (True if redis_claims else None),
    )


def _user(bot_lang: str = "ru") -> User:
    return User(id=17, user_id="123456", system=SystemEnum.max, language_code=bot_lang)


def test_callback_denies_message_from_another_tenant_or_user(monkeypatch) -> None:
    # incoming=None simulates the tenant/user-scoped query finding nothing —
    # exactly what happens if message_ref belongs to another bot or user.
    session = _FakeSession(user=_user(), incoming=None)
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={"user_id": "123456", "system": "max", "message_ref": "42", "action": "call_staff"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "cross_tenant_ai_callback"
    assert session.commits == 0


def test_callback_denies_unknown_user(monkeypatch) -> None:
    session = _FakeSession(user=None)
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={"user_id": "999999", "system": "max", "message_ref": "42", "action": "call_staff"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "cross_tenant_ai_callback"


def test_callback_rejects_invalid_message_ref(monkeypatch) -> None:
    session = _FakeSession(user=_user())
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={"user_id": "123456", "system": "max", "message_ref": "not-an-id", "action": "call_staff"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_message_ref"


def test_callback_call_staff_creates_marker_and_confirms(monkeypatch) -> None:
    incoming = Message(
        id=42,
        bot_instance_id=1,
        user_id=17,
        system=SystemEnum.max,
        direction=MessageDirectionEnum.in_,
        text="расскажите про общагу",
    )
    session = _FakeSession(user=_user(), incoming=incoming)
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={"user_id": "123456", "system": "max", "message_ref": "42", "action": "call_staff"},
    )

    assert response.status_code == 200
    assert "поддержки" in response.json()["text"]
    assert session.commits == 1
    assert len(session.added) == 1
    marker = session.added[0]
    assert marker.direction == MessageDirectionEnum.in_
    assert marker.ai_classification == "kb_staff_requested"


def test_callback_select_delivers_document_and_marks_answered(monkeypatch) -> None:
    incoming = Message(
        id=42,
        bot_instance_id=1,
        user_id=17,
        system=SystemEnum.max,
        direction=MessageDirectionEnum.in_,
        text="расскажите про общагу",
        is_ai_answered=False,
    )
    document = KbDocumentRecord(
        id=7, bot_instance_id=1, topic="Общежитие", content="Заселение с 1 сентября"
    )
    session = _FakeSession(user=_user(), incoming=incoming, document=document)
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={
            "user_id": "123456",
            "system": "max",
            "message_ref": "42",
            "action": "select",
            "document_ref": 7,
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "<b>Общежитие</b>\n\nЗаселение с 1 сентября"
    assert incoming.is_ai_answered is True
    assert session.commits == 1
    outgoing = session.added[0]
    assert outgoing.text == "Общежитие\n\nЗаселение с 1 сентября"
    assert outgoing.ai_classification == "kb_selected"
    assert outgoing.kb_document_id == 7


def test_callback_select_rejects_document_from_another_bot(monkeypatch) -> None:
    incoming = Message(
        id=42,
        bot_instance_id=1,
        user_id=17,
        system=SystemEnum.max,
        direction=MessageDirectionEnum.in_,
        text="расскажите про общагу",
    )
    # document=None simulates the bot_instance_id-scoped lookup finding nothing —
    # what happens when document_ref names another tenant's document.
    session = _FakeSession(user=_user(), incoming=incoming, document=None)
    _patch_common(monkeypatch)
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={
            "user_id": "123456",
            "system": "max",
            "message_ref": "42",
            "action": "select",
            "document_ref": 999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "kb_document_unavailable"


def test_callback_is_idempotent_on_replay(monkeypatch) -> None:
    incoming = Message(
        id=42,
        bot_instance_id=1,
        user_id=17,
        system=SystemEnum.max,
        direction=MessageDirectionEnum.in_,
        text="расскажите про общагу",
    )
    session = _FakeSession(user=_user(), incoming=incoming)
    _patch_common(monkeypatch, redis_claims=False)  # ключ уже занят — «уже обработано»
    app = _app(bot_id=1, session=session)

    response = TestClient(app).post(
        "/messages/ai/callback",
        json={"user_id": "123456", "system": "max", "message_ref": "42", "action": "call_staff"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Уже обработано."
    assert session.commits == 0
    assert session.added == []
