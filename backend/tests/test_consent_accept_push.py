"""Integration tests for Task 071 -- a MAX chat confirmation push enqueued when consent is
accepted through the mini-app: the first-time gate (POST /auth/init-data/validate,
`acceptConsent: true`) and a re-accept during the revoke grace window (POST /consent/accept,
session-based). Never for a bot-channel accept (POST /consent/bot/accept) -- that already
confirms in place by editing the existing chat message (see `bot/app/main.py`), so enqueuing a
push there too would double-send (docs/tasks/071).

Follows the FakeDb pattern `test_student_auth_http.py` established for this router family --
the queries these two accept paths issue (a User point lookup/insert, a UserConsentRecord
select, enqueue_push's own User lookup + PushOutbox insert) are simple enough for a hand-rolled
fake session to reproduce faithfully, so this doesn't need the real-Postgres pattern used
elsewhere in this suite for join-heavy queries.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main  # noqa: F401 -- registers every ORM class in Base.metadata by importing every router
# (needed when this file runs in isolation, same reasoning as test_tickets_http.py).
from app.api.deps import CurrentPrincipal, require_student
from app.db.session import get_db
from app.models.enums import SystemEnum
from app.models.push_outbox import PushOutbox
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.consent.infrastructure.models import UserConsentRecord
from app.modules.consent.presentation import router as consent_router_module
from app.modules.consent.presentation.router import router as consent_router
from app.modules.profiles.domain.entities import BotMembership
from app.modules.profiles.infrastructure.models import User
from app.modules.profiles.presentation import auth_router as auth_router_module
from app.modules.profiles.presentation.auth_router import router as auth_router
from app.modules.tenancy.presentation.dependencies import resolve_tenant
from app.services.max_validation import InitData


class _Scalar:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDb:
    def __init__(
        self,
        *,
        user: User | None = None,
        consent: UserConsentRecord | None = None,
    ) -> None:
        self._users_by_id: dict[int, User] = {user.id: user} if user else {}
        self._consent = consent
        self._next_id = 1000
        self.commits = 0
        self.added: list[object] = []

    def execute(self, stmt):
        # bump_consent_funnel issues a bare upsert `Insert`, not a `select()` -- no
        # `column_descriptions` to introspect, and nothing in this test suite reads its
        # result, so it's a no-op here.
        if not hasattr(stmt, "column_descriptions"):
            return _Scalar(None)
        entity = stmt.column_descriptions[0]["entity"] if stmt.column_descriptions else None
        if entity is UserConsentRecord:
            return _Scalar(self._consent)
        return _Scalar(next(iter(self._users_by_id.values()), None))

    def add(self, obj: object) -> None:
        self.added.append(obj)
        if isinstance(obj, User) and obj.id is None:
            # Mimics what a real flush + refresh against Postgres would fill in for the
            # column defaults the router doesn't set explicitly on a brand-new User.
            obj.phone_verified = False
            obj.shared_data = {}
            obj.ban_chat = False
            obj.ban_forms = False
            obj.ban_app = False
            obj.id = self._next_id
            self._next_id += 1
            self._users_by_id[obj.id] = obj

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _obj: object) -> None:
        pass

    def get(self, model, id):
        if model is User:
            return self._users_by_id.get(id)
        return None

    @property
    def pushes(self) -> list[PushOutbox]:
        return [o for o in self.added if isinstance(o, PushOutbox)]


class FakeProfileGateway:
    def __init__(self, membership: BotMembership | None = None) -> None:
        self._membership = membership

    def get_membership(self, bot_instance_id: int, user_id: int) -> BotMembership | None:
        return self._membership

    def create_membership(self, membership: BotMembership) -> BotMembership:
        self._membership = replace(membership, id=1)
        return self._membership


def _init_data(*, user_id: str = "max-1") -> InitData:
    return InitData(
        raw="raw",
        user_id=user_id,
        username="ivan",
        first_name="Ivan",
        last_name=None,
        photo_url=None,
        language_code="ru",
        auth_date=0,
        start_param=None,
        user={},
        chat=None,
    )


def _bot(id: int = 2) -> BotInstance:
    return BotInstance(id=id, slug=f"bot-{id}", name=f"Бот {id}")


def _existing_user(id: int = 42, *, user_id: str = "max-1") -> User:
    return User(
        id=id,
        user_id=user_id,
        system=SystemEnum.max,
        phone_verified=False,
        shared_data={},
        ban_chat=False,
        ban_forms=False,
        ban_app=False,
    )


def _active_consent(*, external_user_id: str = "max-1") -> UserConsentRecord:
    return UserConsentRecord(
        id=1,
        external_user_id=external_user_id,
        system=SystemEnum.max,
        given_at=datetime(2026, 1, 1, tzinfo=UTC),
        revoked_at=None,
        deletion_due_at=None,
        deleted_at=None,
        policy_version="v1",
    )


def _revoked_consent(*, external_user_id: str = "max-1") -> UserConsentRecord:
    return UserConsentRecord(
        id=5,
        external_user_id=external_user_id,
        system=SystemEnum.max,
        given_at=datetime(2026, 1, 1, tzinfo=UTC),
        revoked_at=datetime(2026, 1, 5, tzinfo=UTC),
        deletion_due_at=datetime(2026, 1, 19, tzinfo=UTC),
        deleted_at=None,
        policy_version="v1",
    )


# --- Mini-app first-time accept: POST /auth/init-data/validate -----------------------------


def _auth_app(
    *, db: FakeDb, monkeypatch, bot: BotInstance, init_data: InitData, membership: BotMembership
) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router, prefix="/auth")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[resolve_tenant] = lambda: bot
    monkeypatch.setattr(auth_router_module, "_resolve_system_token", lambda *_a, **_k: "bot-token")
    monkeypatch.setattr(auth_router_module, "validate_init_data", lambda *_a, **_k: init_data)
    monkeypatch.setattr(
        auth_router_module, "SqlAlchemyProfileGateway", lambda _db: FakeProfileGateway(membership)
    )
    return app


def test_first_time_mini_app_accept_enqueues_consent_push(monkeypatch) -> None:
    db = FakeDb(consent=None)
    membership = BotMembership(id=1, bot_instance_id=2, user_id=1000, is_active=True)
    app = _auth_app(
        db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership
    )

    response = TestClient(app).post(
        "/auth/init-data/validate",
        json={"initData": "whatever", "system": "max", "acceptConsent": True},
    )

    assert response.status_code == 200
    assert len(db.pushes) == 1
    push = db.pushes[0]
    assert push.kind == "consent_accepted"
    assert push.bot_instance_id == 2
    assert push.user_id == 1000
    assert push.payload["given_at"]


def test_gate_shown_without_accept_flag_enqueues_no_push(monkeypatch) -> None:
    db = FakeDb(consent=None)
    membership = BotMembership(id=1, bot_instance_id=2, user_id=1000, is_active=True)
    app = _auth_app(
        db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership
    )

    response = TestClient(app).post(
        "/auth/init-data/validate", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 403
    assert db.pushes == []


def test_already_active_accept_call_enqueues_no_second_push(monkeypatch) -> None:
    db = FakeDb(user=_existing_user(), consent=_active_consent())
    membership = BotMembership(id=1, bot_instance_id=2, user_id=42, is_active=True)
    app = _auth_app(
        db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership
    )

    response = TestClient(app).post(
        "/auth/init-data/validate", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 200
    assert db.pushes == []


def test_inactive_membership_enqueues_no_push(monkeypatch) -> None:
    db = FakeDb(consent=None)
    membership = BotMembership(id=1, bot_instance_id=2, user_id=1000, is_active=False)
    app = _auth_app(
        db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership
    )

    response = TestClient(app).post(
        "/auth/init-data/validate",
        json={"initData": "whatever", "system": "max", "acceptConsent": True},
    )

    assert response.status_code == 403
    assert db.pushes == []


# --- Mini-app re-accept during the grace window: POST /consent/accept ----------------------


def _consent_app(*, db: FakeDb, principal: CurrentPrincipal) -> FastAPI:
    app = FastAPI()
    app.include_router(consent_router, prefix="/consent")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_student] = lambda: principal
    return app


def test_reaccept_during_grace_window_enqueues_push() -> None:
    db = FakeDb(user=_existing_user(id=7, user_id="max-2"), consent=_revoked_consent(external_user_id="max-2"))
    principal = CurrentPrincipal(
        sub="u:7", role="student", system="max", user_id=7, admin_id=None, bot_instance_id=2
    )
    app = _consent_app(db=db, principal=principal)

    response = TestClient(app).post("/consent/accept")

    assert response.status_code == 200
    assert len(db.pushes) == 1
    push = db.pushes[0]
    assert push.kind == "consent_accepted"
    assert push.bot_instance_id == 2
    assert push.user_id == 7
    assert push.payload["given_at"]


def test_reaccept_when_already_active_enqueues_no_push() -> None:
    db = FakeDb(user=_existing_user(id=7, user_id="max-2"), consent=_active_consent(external_user_id="max-2"))
    principal = CurrentPrincipal(
        sub="u:7", role="student", system="max", user_id=7, admin_id=None, bot_instance_id=2
    )
    app = _consent_app(db=db, principal=principal)

    response = TestClient(app).post("/consent/accept")

    assert response.status_code == 200
    assert db.pushes == []


# --- Bot-channel accept never pushes: POST /consent/bot/accept -----------------------------


def test_bot_channel_accept_enqueues_no_push(monkeypatch) -> None:
    """Confirms in place by editing the chat message (Task 064) -- a push here would
    double-send the same confirmation."""
    db = FakeDb(consent=None)
    monkeypatch.setattr(consent_router_module, "authorize_bot_runtime", lambda *_a, **_k: None)
    app = FastAPI()
    app.include_router(consent_router, prefix="/consent")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[resolve_tenant] = lambda: _bot()

    response = TestClient(app).post(
        "/consent/bot/accept", json={"user_id": "max-3", "system": "max"}
    )

    assert response.status_code == 200
    assert db.pushes == []
