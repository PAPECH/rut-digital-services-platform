from __future__ import annotations

from importlib import import_module

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import AdminRoleEnum
from app.modules.admin_invites.presentation import bot_router, platform_router
from app.modules.admins.infrastructure.models import Admin
from app.modules.audit.infrastructure.models import AuditLog
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.support_chat.infrastructure.models import StaffFavorite  # noqa: F401
from app.modules.tenancy.presentation.dependencies import resolve_tenant
from app.services.max_validation import InitData

from .admin_invites_fakes import InMemoryInviteRepository, RecordingGrants, SequentialInviteCodec

staff_dependencies = import_module("app.modules.bot_instances.presentation.dependencies")
session_router = import_module("app.modules.admin_sessions.presentation.router")


class FakeSession:
    def __init__(self, admin: Admin | None = None) -> None:
        self.audit: list[AuditLog] = []
        self.admin = admin
        self.commits = 0
        self.rollbacks = 0

    def add(self, value) -> None:
        if isinstance(value, AuditLog):
            self.audit.append(value)

    def execute(self, _stmt):
        return _Scalar(self.admin)

    def get(self, _model, _id):
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _Scalar:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _principal(role: str, admin_id: int = 5) -> CurrentPrincipal:
    return CurrentPrincipal(sub=f"a:{admin_id}", role=role, system="max", user_id=None, admin_id=admin_id)


def _bot(bot_id: int) -> BotInstance:
    return BotInstance(id=bot_id, slug=f"bot-{bot_id}", name=f"Bot {bot_id}")


@pytest.fixture
def repository(monkeypatch) -> InMemoryInviteRepository:
    repository = InMemoryInviteRepository()
    codec = SequentialInviteCodec()
    for module in (bot_router, platform_router, session_router):
        monkeypatch.setattr(module, "SqlAlchemyAdminInviteRepository", lambda _db: repository)
        monkeypatch.setattr(module, "HmacInviteTokenCodec", lambda: codec)
    monkeypatch.setattr(settings, "MAX_BOT_USERNAME", "@platform_bot")
    return repository


def _bot_app(session: FakeSession, *, bot_id: int, role: str = "admin", manages: set[int] | None = None):
    app = FastAPI()
    app.include_router(bot_router.router, prefix="/instances")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_principal] = lambda: _principal(role)
    app.dependency_overrides[resolve_tenant] = lambda: _bot(bot_id)
    allowed = {1} if manages is None else manages
    staff_dependencies.admin_has_bot_permission = (  # type: ignore[attr-defined]
        lambda _db, principal, bot, *_flags: principal.is_platform_admin or bot in allowed
    )
    return TestClient(app)


@pytest.fixture(autouse=True)
def _restore_permission_check():
    original = staff_dependencies.admin_has_bot_permission
    yield
    staff_dependencies.admin_has_bot_permission = original


def _create_bot_invite(client: TestClient, **overrides):
    body = {"full_name": "Петров Пётр", "permissions": {"can_manage_forms": True}, **overrides}
    return client.post("/instances/current/admin-invites", json=body)


def test_bot_invite_returns_link_once_and_audits_without_personal_data(repository) -> None:
    session = FakeSession()
    client = _bot_app(session, bot_id=1)

    created = _create_bot_invite(client, max_uses=3)
    listed = client.get("/instances/current/admin-invites")

    assert created.status_code == 201
    body = created.json()
    assert body["link"] == f"https://max.ru/platform_bot?startapp={body['start_param']}"
    assert body["start_param"].startswith("inv_")
    assert body["invite"]["status"] == "active"
    assert body["invite"]["permissions"]["can_manage_forms"] is True
    assert "start_param" not in listed.json()[0] and "link" not in listed.json()[0]
    assert repository.items[1].bot_instance_id == 1
    meta = session.audit[0].meta
    assert meta["action"] == "admin_invite_created"
    assert "Петров" not in str(meta)


def test_bot_invite_rejects_unknown_fields_and_bot_id_in_body(repository) -> None:
    client = _bot_app(FakeSession(), bot_id=1)

    response = _create_bot_invite(client, bot_instance_id=2)

    assert response.status_code == 422
    assert repository.items == {}


def test_admin_of_other_bot_cannot_list_create_or_revoke(repository) -> None:
    _create_bot_invite(_bot_app(FakeSession(), bot_id=1))
    other = _bot_app(FakeSession(), bot_id=2, manages={1, 2})

    assert other.get("/instances/current/admin-invites").json() == []
    assert other.delete("/instances/current/admin-invites/1").status_code == 404
    assert repository.items[1].revoked_at is None


def test_bot_invites_require_staff_management(repository) -> None:
    client = _bot_app(FakeSession(), bot_id=1, manages=set())

    assert _create_bot_invite(client).status_code == 403
    assert client.get("/instances/current/admin-invites").status_code == 403
    assert repository.items == {}


def test_employee_role_cannot_manage_invites(repository) -> None:
    client = _bot_app(FakeSession(), bot_id=1, role="employee")

    assert _create_bot_invite(client).status_code == 403


def _platform_app(session: FakeSession, role: str):
    app = FastAPI()
    app.include_router(platform_router.router, prefix="/platform-admins")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_principal] = lambda: _principal(role)
    return TestClient(app)


def test_platform_invites_are_platform_admin_only(repository) -> None:
    client = _platform_app(FakeSession(), "admin")

    assert client.post("/platform-admins/invites", json={"full_name": "Иван"}).status_code == 403
    assert client.get("/platform-admins/invites").status_code == 403
    assert client.delete("/platform-admins/invites/1").status_code == 403


def test_platform_invite_lifecycle(repository) -> None:
    client = _platform_app(FakeSession(), "platform_admin")

    created = client.post("/platform-admins/invites", json={"full_name": "Иван", "ttl_hours": 2})
    revoked = client.delete(f"/platform-admins/invites/{created.json()['invite']['id']}")
    listed = client.get("/platform-admins/invites").json()

    assert created.status_code == 201
    assert created.json()["invite"]["role"] is None
    assert revoked.status_code == 204
    assert listed[0]["status"] == "revoked"


def test_platform_invite_is_invisible_from_bot_endpoints(repository) -> None:
    _platform_app(FakeSession(), "platform_admin").post(
        "/platform-admins/invites", json={"full_name": "Иван"}
    )
    client = _bot_app(FakeSession(), bot_id=1)

    assert client.get("/instances/current/admin-invites").json() == []
    assert client.delete("/instances/current/admin-invites/1").status_code == 404


def _login_app(monkeypatch, session: FakeSession, grants: RecordingGrants, start_param: str):
    init = InitData(
        raw="raw",
        user_id="max-7",
        username=None,
        first_name="Пётр",
        last_name=None,
        photo_url=None,
        language_code="ru",
        auth_date=0,
        start_param=start_param,
        user={},
        chat=None,
    )
    monkeypatch.setattr(session_router, "validate_init_data", lambda *_a, **_k: init)
    monkeypatch.setattr(session_router, "UseCaseInviteGrants", lambda _db: grants)
    monkeypatch.setattr(session_router, "StartAdminSession", _FakeStart)
    app = FastAPI()
    app.include_router(session_router.router, prefix="/api/auth")
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


class _Issued:
    raw_token = "refresh-token"


class _FakeStart:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def execute(self, *_args, **_kwargs) -> _Issued:
        return _Issued()


def _invite_start_param(repository) -> str:
    client = _bot_app(FakeSession(), bot_id=1)
    return _create_bot_invite(client).json()["start_param"]


def test_login_with_invite_grants_access_and_starts_session(monkeypatch, repository) -> None:
    start_param = _invite_start_param(repository)
    admin = Admin(id=100, max_user_id="max-7", full_name="Петров Пётр", role=AdminRoleEnum.employee, is_active=True)
    session = FakeSession(admin=admin)
    grants = RecordingGrants()
    client = _login_app(monkeypatch, session, grants, start_param)

    response = client.post("/api/auth/admin/login", json={"initData": "x", "system": "max"})

    assert response.status_code == 200
    assert response.json()["admin"]["id"] == 100
    assert grants.bot_staff[0][:2] == (1, "max-7")
    assert repository.items[1].used_count == 1
    redeemed = [entry.meta for entry in session.audit if entry.meta["action"] == "admin_invite_redeemed"]
    assert redeemed and "max-7" not in str(redeemed) and "Петров" not in str(redeemed)


@pytest.mark.parametrize(
    ("start_param", "status", "code"),
    [
        ("inv_unknown-token-value-000", 403, "invite_invalid"),
        ("inv_!!", 400, "bad_start_param"),
    ],
)
def test_login_with_invalid_invite_is_rejected(monkeypatch, repository, start_param, status, code) -> None:
    session = FakeSession(admin=None)
    grants = RecordingGrants()
    client = _login_app(monkeypatch, session, grants, start_param)

    response = client.post("/api/auth/admin/login", json={"initData": "x", "system": "max"})

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    assert grants.bot_staff == [] and grants.platform == []


def test_login_with_invite_for_inactive_staff_is_rejected(monkeypatch, repository) -> None:
    start_param = _invite_start_param(repository)
    session = FakeSession(admin=None)
    client = _login_app(monkeypatch, session, RecordingGrants(inactive={"max-7"}), start_param)

    response = client.post("/api/auth/admin/login", json={"initData": "x", "system": "max"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "admin_inactive"
    assert repository.items[1].used_count == 0
