from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal, require_student
from app.db.session import get_db
from app.models.enums import AdminRoleEnum, SystemEnum
from app.modules.admins.infrastructure.models import Admin
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.consent.infrastructure.models import UserConsentRecord
from app.modules.profiles.domain.entities import BotMembership
from app.modules.profiles.infrastructure.models import User
from app.modules.profiles.presentation import auth_router as auth_router_module
from app.modules.profiles.presentation.auth_router import router
from app.modules.tenancy.presentation.dependencies import resolve_tenant
from app.services.max_validation import InitData


def _active_consent() -> UserConsentRecord:
    """Default consent fixture for tests that aren't about the consent gate itself --
    keeps every pre-existing test exercising its original intent (user creation, profile
    refill, membership checks) unaffected by Task 064's gate now sitting in front of
    /auth/init-data/validate. Tests that ARE about the gate pass their own value."""
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


class FakeProfileGateway:
    def __init__(self, membership: BotMembership | None = None) -> None:
        self._membership = membership

    def get_membership(self, bot_instance_id: int, user_id: int) -> BotMembership | None:
        return self._membership

    def create_membership(self, membership: BotMembership) -> BotMembership:
        self._membership = replace(membership, id=1)
        return self._membership


class _ScalarResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDb:
    def __init__(
        self,
        *,
        user_lookup_result: User | None = None,
        users_by_id: dict[int, User] | None = None,
        admins_by_id: dict[int, Admin] | None = None,
        consent_lookup_result: UserConsentRecord | None = "__default_active__",
    ) -> None:
        self._user_lookup_result = user_lookup_result
        self._users_by_id = dict(users_by_id or {})
        self._admins_by_id = admins_by_id or {}
        self._consent_lookup_result = (
            _active_consent() if consent_lookup_result == "__default_active__" else consent_lookup_result
        )
        self._next_id = 1000
        self.commits = 0
        self.added: list[object] = []

    def execute(self, stmt):
        entity = stmt.column_descriptions[0]["entity"] if stmt.column_descriptions else None
        if entity is UserConsentRecord:
            return _ScalarResult(self._consent_lookup_result)
        return _ScalarResult(self._user_lookup_result)

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
        if model is Admin:
            return self._admins_by_id.get(id)
        return None


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


def _user(id: int, *, user_id: str = "max-1", username: str | None = None) -> User:
    return User(
        id=id,
        user_id=user_id,
        system=SystemEnum.max,
        username=username,
        phone_verified=False,
        shared_data={},
        ban_chat=False,
        ban_forms=False,
        ban_app=False,
    )


def _app(
    *,
    db: FakeDb,
    monkeypatch,
    bot: BotInstance | None = None,
    init_data: InitData | None = None,
    membership: BotMembership | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/auth")
    app.dependency_overrides[get_db] = lambda: db
    if bot is not None:
        app.dependency_overrides[resolve_tenant] = lambda: bot
    monkeypatch.setattr(auth_router_module, "_resolve_system_token", lambda *_a, **_k: "bot-token")
    if init_data is not None:
        monkeypatch.setattr(auth_router_module, "validate_init_data", lambda *_a, **_k: init_data)
    monkeypatch.setattr(
        auth_router_module, "SqlAlchemyProfileGateway", lambda _db: FakeProfileGateway(membership)
    )
    return app


def test_init_data_validate_creates_new_user_and_membership(monkeypatch) -> None:
    db = FakeDb(user_lookup_result=None)
    membership = BotMembership(id=1, bot_instance_id=2, user_id=1000, is_active=True)
    app = _app(db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership)

    response = TestClient(app).post(
        "/auth/init-data/validate", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["user_id"] == "max-1"
    assert body["token"]["role"] == "student"
    assert db.commits == 1


def test_init_data_validate_updates_existing_user(monkeypatch) -> None:
    existing = _user(42, username="old")
    db = FakeDb(user_lookup_result=existing, users_by_id={42: existing})
    membership = BotMembership(id=1, bot_instance_id=2, user_id=42, is_active=True)
    app = _app(
        db=db,
        monkeypatch=monkeypatch,
        bot=_bot(),
        init_data=_init_data(),
        membership=membership,
    )

    response = TestClient(app).post(
        "/auth/init-data/validate", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == 42
    assert existing.username == "ivan"


def test_init_data_validate_rejects_inactive_membership(monkeypatch) -> None:
    db = FakeDb(user_lookup_result=None)
    membership = BotMembership(id=1, bot_instance_id=2, user_id=1000, is_active=False)
    app = _app(db=db, monkeypatch=monkeypatch, bot=_bot(), init_data=_init_data(), membership=membership)

    response = TestClient(app).post(
        "/auth/init-data/validate", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "membership_inactive"


def test_phone_verify_accepts_valid_signature(monkeypatch) -> None:
    user = User(id=1, user_id="max-1", system=SystemEnum.max)
    db = FakeDb(users_by_id={1: user})
    app = _app(db=db, monkeypatch=monkeypatch)
    monkeypatch.setattr(auth_router_module, "validate_contact", lambda **_k: True)
    principal = CurrentPrincipal(
        sub="u:1", role="student", system="max", user_id=1, admin_id=None, bot_instance_id=2
    )
    app.dependency_overrides[require_student] = lambda: principal

    response = TestClient(app).post(
        "/auth/phone/verify",
        json={"phone": "+70000000000", "authDate": 0, "hash": "x", "system": "max"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "phone": "+70000000000", "verified": True}
    assert user.phone_verified is True


def test_phone_verify_rejects_invalid_signature(monkeypatch) -> None:
    user = User(id=1, user_id="max-1", system=SystemEnum.max)
    db = FakeDb(users_by_id={1: user})
    app = _app(db=db, monkeypatch=monkeypatch)
    monkeypatch.setattr(auth_router_module, "validate_contact", lambda **_k: False)
    principal = CurrentPrincipal(
        sub="u:1", role="student", system="max", user_id=1, admin_id=None, bot_instance_id=2
    )
    app.dependency_overrides[require_student] = lambda: principal

    response = TestClient(app).post(
        "/auth/phone/verify",
        json={"phone": "+70000000000", "authDate": 0, "hash": "x", "system": "max"},
    )

    assert response.status_code == 400


def test_me_returns_student_shape(monkeypatch) -> None:
    user = _user(1)
    db = FakeDb(users_by_id={1: user})
    app = _app(db=db, monkeypatch=monkeypatch)
    principal = CurrentPrincipal(
        sub="u:1", role="student", system="max", user_id=1, admin_id=None, bot_instance_id=2
    )
    app.dependency_overrides[get_current_principal] = lambda: principal

    response = TestClient(app).get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["user"]["user_id"] == "max-1"


def test_me_returns_admin_shape_for_staff(monkeypatch) -> None:
    admin = Admin(id=5, max_user_id="max-5", full_name="Ivan", role=AdminRoleEnum.admin, is_active=True)
    db = FakeDb(admins_by_id={5: admin})
    app = _app(db=db, monkeypatch=monkeypatch)
    principal = CurrentPrincipal(sub="a:5", role="admin", system="max", user_id=None, admin_id=5)
    app.dependency_overrides[get_current_principal] = lambda: principal

    response = TestClient(app).get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["admin"]["max_user_id"] == "max-5"


def test_me_without_resolvable_subject_is_unauthorized(monkeypatch) -> None:
    db = FakeDb()
    app = _app(db=db, monkeypatch=monkeypatch)
    principal = CurrentPrincipal(sub="?", role="student", system="max", user_id=None, admin_id=None)
    app.dependency_overrides[get_current_principal] = lambda: principal

    response = TestClient(app).get("/auth/me")

    assert response.status_code == 401
