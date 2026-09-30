from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.modules.admin_sessions.domain.entities import AdminRefreshSession
from app.modules.admin_sessions.presentation.router import router
from app.modules.admins.infrastructure.models import Admin
from app.models.enums import AdminRoleEnum
from app.services.max_validation import InitData

admin_session_router_module = import_module("app.modules.admin_sessions.presentation.router")


class SequentialCodec:
    def __init__(self) -> None:
        self.counter = 0

    def generate(self) -> str:
        self.counter += 1
        return f"raw-token-{self.counter}"

    def digest(self, raw_token: str) -> str:
        return f"digest:{raw_token}"


class InMemorySessionRepository:
    def __init__(self) -> None:
        self.items: dict[int, AdminRefreshSession] = {}
        self.next_id = 1

    def add(self, session: AdminRefreshSession) -> AdminRefreshSession:
        stored = replace(session, id=self.next_id)
        self.items[self.next_id] = stored
        self.next_id += 1
        return stored

    def get_by_hash(self, token_hash: str, *, for_update: bool = False) -> AdminRefreshSession | None:
        del for_update
        return next((item for item in self.items.values() if item.token_hash == token_hash), None)

    def mark_rotated(self, session_id: int, *, replaced_by_id: int, used_at: datetime) -> None:
        self.items[session_id] = replace(
            self.items[session_id], replaced_by_id=replaced_by_id, revoked_at=used_at, last_used_at=used_at
        )

    def revoke_family(self, family_id: str, *, revoked_at: datetime) -> None:
        for session_id, item in list(self.items.items()):
            if item.family_id == family_id and item.revoked_at is None:
                self.items[session_id] = replace(item, revoked_at=revoked_at)


class FakeDb:
    def __init__(self, *, login_lookup_result: Admin | None = None, admins_by_id: dict[int, Admin] | None = None):
        self._login_lookup_result = login_lookup_result
        self._admins_by_id = admins_by_id or {}
        self.commits = 0
        self.rollbacks = 0

    def execute(self, _stmt):
        return _ScalarResult(self._login_lookup_result)

    def get(self, model, id):
        if model is Admin:
            return self._admins_by_id.get(id)
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _ScalarResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _init_data(*, user_id: str = "max-1", start_param: str | None = None) -> InitData:
    return InitData(
        raw="raw",
        user_id=user_id,
        username="ivan",
        first_name="Ivan",
        last_name=None,
        photo_url=None,
        language_code="ru",
        auth_date=0,
        start_param=start_param,
        user={},
        chat=None,
    )


def _admin(id: int = 1, *, is_active: bool = True) -> Admin:
    return Admin(
        id=id, max_user_id="max-1", full_name="Ivan Ivanov", role=AdminRoleEnum.admin, is_active=is_active
    )


def _app(*, db: FakeDb, monkeypatch, init_data: InitData | None = None) -> tuple[FastAPI, InMemorySessionRepository]:
    app = FastAPI()
    # Mounted at /api/auth (not /auth) to match `_set_admin_cookies`' hardcoded
    # `path="/api/auth"` cookie scope -- otherwise the test client's cookie jar correctly
    # refuses to resend the refresh cookie on a path outside its scope.
    app.include_router(router, prefix="/api/auth")
    app.dependency_overrides[get_db] = lambda: db
    repository = InMemorySessionRepository()
    codec = SequentialCodec()
    monkeypatch.setattr(
        admin_session_router_module, "SqlAlchemyAdminSessionRepository", lambda _db: repository
    )
    monkeypatch.setattr(admin_session_router_module, "HmacRefreshTokenCodec", lambda: codec)
    if init_data is not None:
        monkeypatch.setattr(
            admin_session_router_module, "validate_init_data", lambda *_a, **_k: init_data
        )
    return app, repository


def test_admin_login_happy_path(monkeypatch) -> None:
    db = FakeDb(login_lookup_result=_admin())
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="admin_login"))

    response = TestClient(app).post(
        "/api/auth/admin/login", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["admin"]["max_user_id"] == "max-1"
    assert body["token"]["role"] == "admin"
    assert "platform_admin_refresh" in response.cookies
    assert "platform_admin_csrf" in response.cookies


def test_admin_login_rejects_unknown_admin(monkeypatch) -> None:
    db = FakeDb(login_lookup_result=None)
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data())

    response = TestClient(app).post(
        "/api/auth/admin/login", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 403


def test_admin_login_rejects_bad_start_param(monkeypatch) -> None:
    db = FakeDb(login_lookup_result=_admin())
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="something_else"))

    response = TestClient(app).post(
        "/api/auth/admin/login", json={"initData": "whatever", "system": "max"}
    )

    assert response.status_code == 400


def test_admin_login_refresh_logout_round_trip(monkeypatch) -> None:
    admin = _admin()
    db = FakeDb(login_lookup_result=admin, admins_by_id={admin.id: admin})
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="admin_login"))
    client = TestClient(app)

    login = client.post("/api/auth/admin/login", json={"initData": "whatever", "system": "max"})
    assert login.status_code == 200
    csrf = login.cookies["platform_admin_csrf"]

    refreshed = client.post("/api/auth/admin/refresh", headers={"x-csrf-token": csrf})
    assert refreshed.status_code == 200
    new_csrf = refreshed.cookies["platform_admin_csrf"]

    logout = client.post("/api/auth/admin/logout", headers={"x-csrf-token": new_csrf})
    assert logout.status_code == 204
    assert "platform_admin_refresh" not in logout.cookies or logout.cookies.get("platform_admin_refresh") == ""


def test_admin_refresh_rejects_missing_csrf(monkeypatch) -> None:
    admin = _admin()
    db = FakeDb(login_lookup_result=admin, admins_by_id={admin.id: admin})
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="admin_login"))
    client = TestClient(app)

    client.post("/api/auth/admin/login", json={"initData": "whatever", "system": "max"})
    response = client.post("/api/auth/admin/refresh")

    assert response.status_code == 403


def test_admin_refresh_detects_reuse(monkeypatch) -> None:
    admin = _admin()
    db = FakeDb(login_lookup_result=admin, admins_by_id={admin.id: admin})
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="admin_login"))
    client = TestClient(app)

    login = client.post("/api/auth/admin/login", json={"initData": "whatever", "system": "max"})
    csrf = login.cookies["platform_admin_csrf"]
    old_refresh_cookie = login.cookies["platform_admin_refresh"]

    first_refresh = client.post("/api/auth/admin/refresh", headers={"x-csrf-token": csrf})
    assert first_refresh.status_code == 200
    new_csrf = first_refresh.cookies["platform_admin_csrf"]

    # Re-send the *old* (now-rotated) refresh cookie to simulate reuse, keeping the CSRF
    # cookie/header pair in sync with what the jar now actually holds after rotation.
    client.cookies.set("platform_admin_refresh", old_refresh_cookie)
    replay = client.post("/api/auth/admin/refresh", headers={"x-csrf-token": new_csrf})

    assert replay.status_code == 401
    assert replay.json()["detail"]["code"] == "refresh_reuse_detected"


def test_admin_refresh_rejects_deactivated_admin(monkeypatch) -> None:
    admin = _admin()
    db = FakeDb(login_lookup_result=admin, admins_by_id={admin.id: admin})
    app, _ = _app(db=db, monkeypatch=monkeypatch, init_data=_init_data(start_param="admin_login"))
    client = TestClient(app)

    login = client.post("/api/auth/admin/login", json={"initData": "whatever", "system": "max"})
    csrf = login.cookies["platform_admin_csrf"]

    db._admins_by_id[admin.id] = _admin(is_active=False)
    response = client.post("/api/auth/admin/refresh", headers={"x-csrf-token": csrf})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "admin_inactive"
