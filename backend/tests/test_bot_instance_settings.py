from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, require_admin
from app.core.errors import ApiError, forbidden
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.bot_instances.domain.settings import Setting
from app.modules.bot_instances.presentation import dependencies as bot_instances_deps
from app.modules.bot_instances.presentation import settings_router as settings_router_module
from app.modules.bot_instances.presentation.dependencies import authorize_setting_read
from app.modules.bot_instances.presentation.settings_router import router
from app.modules.tenancy.presentation.dependencies import require_tenant_access, resolve_tenant


class _AccessQueryResult:
    def __init__(self, value: int | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> int | None:
        return self._value


class FakeAccessSession:
    """Fakes the one `db.execute(select(AdminBotAccessRecord.id)...)` call
    `authorize_setting_read` makes for the staff branch."""

    def __init__(self, has_access: bool) -> None:
        self._has_access = has_access

    def execute(self, _stmt) -> _AccessQueryResult:
        return _AccessQueryResult(1 if self._has_access else None)


class FakeSettingRepository:
    def __init__(self, store: dict[tuple[int, str], str | None]) -> None:
        self._store = store

    def get(self, bot_instance_id: int, key: str) -> Setting | None:
        if (bot_instance_id, key) not in self._store:
            return None
        return Setting(
            bot_instance_id=bot_instance_id, key=key, value=self._store[(bot_instance_id, key)]
        )

    def list_for_bot(self, bot_instance_id: int) -> list[Setting]:
        return [
            Setting(bot_instance_id=bid, key=k, value=v)
            for (bid, k), v in sorted(self._store.items())
            if bid == bot_instance_id
        ]

    def upsert(self, bot_instance_id: int, key: str, value: str | None) -> Setting:
        self._store[(bot_instance_id, key)] = value
        return Setting(bot_instance_id=bot_instance_id, key=key, value=value)

    def delete(self, bot_instance_id: int, key: str) -> bool:
        if (bot_instance_id, key) not in self._store:
            return False
        del self._store[(bot_instance_id, key)]
        return True


def _admin_principal(admin_id: int = 5) -> CurrentPrincipal:
    return CurrentPrincipal(
        sub=f"a:{admin_id}", role="admin", system="max", user_id=None, admin_id=admin_id
    )


def _admin_token(*, admin_id: int) -> str:
    return create_access_token({"sub": f"a:{admin_id}", "role": "employee", "admin_id": admin_id})


def _student_token(*, bot_instance_id: int) -> str:
    return create_access_token(
        {"sub": "u:1", "role": "student", "user_pk": 1, "bot_instance_id": bot_instance_id}
    )


def _platform_admin_token() -> str:
    return create_access_token({"sub": "a:1", "role": "platform_admin", "admin_id": 1})


def _app(*, bot: BotInstance, store: dict, monkeypatch, with_admin: bool = False) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/settings")
    app.dependency_overrides[resolve_tenant] = lambda: bot
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: None
    if with_admin:
        app.dependency_overrides[require_admin] = lambda: _admin_principal()
    monkeypatch.setattr(
        settings_router_module,
        "SqlAlchemySettingRepository",
        lambda _db: FakeSettingRepository(store),
    )
    return app


# --- authorize_setting_read: unit tests -------------------------------------------------


def test_authorize_setting_read_trusts_bot_runtime_token(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        bot_instances_deps,
        "authorize_bot_runtime",
        lambda _db, bot_id, _rt, _legacy: calls.append(bot_id),
    )

    authorize_setting_read("legacy-token", None, None, 2, db=None)  # type: ignore[arg-type]

    assert calls == [2]


def test_authorize_setting_read_rejects_missing_credentials() -> None:
    with pytest.raises(ApiError) as error:
        authorize_setting_read(None, None, None, 2, db=None)  # type: ignore[arg-type]
    assert error.value.status_code == 401


def test_authorize_setting_read_rejects_invalid_jwt() -> None:
    with pytest.raises(ApiError) as error:
        authorize_setting_read(None, None, "Bearer not-a-jwt", 2, db=None)  # type: ignore[arg-type]
    assert error.value.status_code == 401


def test_authorize_setting_read_allows_platform_admin() -> None:
    token = _platform_admin_token()
    authorize_setting_read(None, None, f"Bearer {token}", 2, db=None)  # type: ignore[arg-type]


def test_authorize_setting_read_allows_student_of_same_bot() -> None:
    token = _student_token(bot_instance_id=2)
    authorize_setting_read(None, None, f"Bearer {token}", 2, db=None)  # type: ignore[arg-type]


def test_authorize_setting_read_denies_student_of_another_bot() -> None:
    token = _student_token(bot_instance_id=1)
    with pytest.raises(ApiError) as error:
        authorize_setting_read(None, None, f"Bearer {token}", 2, db=None)  # type: ignore[arg-type]
    assert error.value.status_code == 403
    assert error.value.detail["code"] == "tenant_access_denied"


def test_authorize_setting_read_allows_staff_with_bot_access() -> None:
    token = _admin_token(admin_id=5)
    authorize_setting_read(None, None, f"Bearer {token}", 2, db=FakeAccessSession(has_access=True))


def test_authorize_setting_read_denies_staff_without_bot_access() -> None:
    token = _admin_token(admin_id=5)
    with pytest.raises(ApiError) as error:
        authorize_setting_read(
            None, None, f"Bearer {token}", 2, db=FakeAccessSession(has_access=False)
        )
    assert error.value.status_code == 403
    assert error.value.detail["code"] == "tenant_access_denied"


# --- GET /settings/{key} at the HTTP boundary -------------------------------------------


def test_get_setting_missing_key_returns_null_value(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={}, monkeypatch=monkeypatch)
    monkeypatch.setattr(bot_instances_deps, "authorize_bot_runtime", lambda *_args: None)

    response = TestClient(app).get("/settings/some_key", headers={"X-Bot-Token": "t"})

    assert response.status_code == 200
    assert response.json() == {"key": "some_key", "value": None}


def test_get_setting_existing_key_returns_value(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={(2, "greeting"): "hello"}, monkeypatch=monkeypatch)
    monkeypatch.setattr(bot_instances_deps, "authorize_bot_runtime", lambda *_args: None)

    response = TestClient(app).get("/settings/greeting", headers={"X-Bot-Token": "t"})

    assert response.status_code == 200
    assert response.json() == {"key": "greeting", "value": "hello"}


def test_get_setting_without_credentials_is_unauthorized(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={}, monkeypatch=monkeypatch)

    response = TestClient(app).get("/settings/some_key")

    assert response.status_code == 401


def test_get_setting_denies_student_of_another_bot_at_http_boundary(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={(2, "greeting"): "hello"}, monkeypatch=monkeypatch)
    token = _student_token(bot_instance_id=1)

    response = TestClient(app).get(
        "/settings/greeting", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_access_denied"


# --- GET/PUT/DELETE admin endpoints ------------------------------------------------------


def test_list_put_delete_require_admin(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={}, monkeypatch=monkeypatch)
    client = TestClient(app)

    assert client.get("/settings").status_code == 401
    assert client.put("/settings/foo", json={"value": "x"}).status_code == 401
    assert client.delete("/settings/foo").status_code == 401


def test_admin_endpoints_deny_cross_tenant_access(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={}, monkeypatch=monkeypatch, with_admin=True)

    def deny() -> BotInstance:
        raise forbidden("No bot access", code="tenant_access_denied")

    app.dependency_overrides[require_tenant_access] = deny
    client = TestClient(app)

    assert client.get("/settings").status_code == 403
    assert client.put("/settings/x", json={"value": "y"}).status_code == 403
    assert client.delete("/settings/x").status_code == 403


def test_put_creates_then_updates_same_key(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    store: dict[tuple[int, str], str | None] = {}
    app = _app(bot=bot, store=store, monkeypatch=monkeypatch, with_admin=True)
    client = TestClient(app)

    created = client.put("/settings/greeting", json={"value": "hi"})
    assert created.status_code == 200
    assert created.json() == {"key": "greeting", "value": "hi"}

    updated = client.put("/settings/greeting", json={"value": "hello"})
    assert updated.status_code == 200
    assert updated.json() == {"key": "greeting", "value": "hello"}
    assert store == {(2, "greeting"): "hello"}


def test_delete_missing_key_returns_404(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    app = _app(bot=bot, store={}, monkeypatch=monkeypatch, with_admin=True)

    response = TestClient(app).delete("/settings/missing")

    assert response.status_code == 404


def test_delete_existing_key_removes_it(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    store: dict[tuple[int, str], str | None] = {(2, "greeting"): "hello"}
    app = _app(bot=bot, store=store, monkeypatch=monkeypatch, with_admin=True)

    response = TestClient(app).delete("/settings/greeting")

    assert response.status_code == 204
    assert store == {}


def test_list_settings_returns_only_this_bots_keys(monkeypatch) -> None:
    bot = BotInstance(id=2, slug="bot-2", name="Бот 2")
    store: dict[tuple[int, str], str | None] = {
        (1, "other_bot_key"): "x",
        (2, "a"): "1",
        (2, "b"): "2",
    }
    app = _app(bot=bot, store=store, monkeypatch=monkeypatch, with_admin=True)

    response = TestClient(app).get("/settings")

    assert response.status_code == 200
    assert response.json() == [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]
