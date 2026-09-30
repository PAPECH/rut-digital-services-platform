from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.capabilities.domain.entities import CapabilityInstallation
from app.modules.capabilities.rut_schedule.application.ports import (
    ProviderGroup,
    ProviderHierarchy,
    ProviderInstitute,
)
from app.modules.capabilities.rut_schedule.domain.entities import ManualSyncRequest
from app.modules.capabilities.rut_schedule.domain.manual_sync import (
    InvalidSyncRequest,
    validate_manual_sync_scope,
)
from app.modules.capabilities.rut_schedule.infrastructure import manual_sync as manual_sync_module
from app.modules.capabilities.rut_schedule.infrastructure.manual_sync import SyncAlreadyRunning
from app.modules.capabilities.rut_schedule.infrastructure.provider import MiitTimetableProviderError
from app.modules.capabilities.rut_schedule.presentation import admin_router as admin_router_module
from app.modules.tenancy.presentation.dependencies import require_tenant_access

# --- Pure domain validation (no I/O) ---


def test_scope_all_with_no_group_or_institute_is_valid() -> None:
    validate_manual_sync_scope("all", None, None, set(), set())


def test_scope_group_requires_group_external_id() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("group", None, None, {"1"}, set())
    assert error.value.path == "group_external_id"


def test_scope_group_rejects_unknown_group() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("group", "999", None, {"1", "2"}, set())
    assert error.value.path == "group_external_id"


def test_scope_group_accepts_known_group() -> None:
    validate_manual_sync_scope("group", "1", None, {"1", "2"}, set())


def test_scope_group_rejects_institute_external_id_too() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("group", "1", "AGA", {"1"}, {"AGA"})
    assert error.value.path == "institute_external_id"


def test_scope_institute_requires_institute_external_id() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("institute", None, None, set(), {"AGA"})
    assert error.value.path == "institute_external_id"


def test_scope_institute_rejects_unknown_institute() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("institute", None, "UNKNOWN", set(), {"AGA"})
    assert error.value.path == "institute_external_id"


def test_scope_institute_accepts_known_institute() -> None:
    validate_manual_sync_scope("institute", None, "AGA", set(), {"AGA"})


def test_scope_institute_rejects_group_external_id_too() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("institute", "1", "AGA", {"1"}, {"AGA"})
    assert error.value.path == "group_external_id"


def test_scope_all_rejects_extraneous_group_external_id() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("all", "1", None, {"1"}, set())
    assert error.value.path == "group_external_id"


def test_scope_all_rejects_extraneous_institute_external_id() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("all", None, "AGA", set(), {"AGA"})
    assert error.value.path == "institute_external_id"


def test_unknown_scope_is_rejected() -> None:
    with pytest.raises(InvalidSyncRequest) as error:
        validate_manual_sync_scope("everything", None, None, set(), set())
    assert error.value.path == "scope"


# --- HTTP boundary: role gating and stable error codes ---


def _bot_admin_principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="a:5", role="admin", system="max", user_id=None, admin_id=5, bot_instance_id=1, bot_slug="bot-1"
    )


def _platform_admin_principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        sub="a:9",
        role="platform_admin",
        system="max",
        user_id=None,
        admin_id=9,
        bot_instance_id=None,
        bot_slug=None,
    )


class _DummySession:
    def add(self, _obj: object) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _app(principal: CurrentPrincipal, bot: BotInstance) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router_module.router)
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: _DummySession()
    # Bypass the real Redis-backed rate limiter -- it isn't the thing under test here, and its
    # state persists across test runs within the same window, which would otherwise make these
    # tests order/timing-dependent.
    app.dependency_overrides[admin_router_module._sync_trigger_limit] = lambda: None
    return app


def test_bot_admin_cannot_trigger_manual_sync() -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_bot_admin_principal(), bot)

    response = TestClient(app).post("/sync", json={"scope": "all"})

    assert response.status_code == 403


def test_bot_admin_cannot_list_sync_requests() -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_bot_admin_principal(), bot)

    response = TestClient(app).get("/sync-requests")

    assert response.status_code == 403


def test_bot_admin_cannot_list_groups_with_last_sync() -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_bot_admin_principal(), bot)

    response = TestClient(app).get("/groups")

    assert response.status_code == 403


def _installed_installation(bot_id: int) -> CapabilityInstallation:
    return CapabilityInstallation(
        id=42,
        bot_instance_id=bot_id,
        capability_key="rut_schedule",
        is_enabled=True,
        config={
            "provider": "miit_timetable",
            "title": "Расписание",
            "subtitle": "sub",
            "group_cache_ttl_seconds": 900,
            "hierarchy_sync_interval_seconds": 21_600,
            "night_auto_sync_enabled": True,
        },
        config_revision=1,
    )


def test_platform_admin_trigger_gets_409_when_sync_already_running(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )

    async def _raise_already_running(*args, **kwargs):
        raise SyncAlreadyRunning(1)

    monkeypatch.setattr(admin_router_module, "enqueue_manual_sync", _raise_already_running)

    response = TestClient(app).post("/sync", json={"scope": "all"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "sync_already_running"


def test_platform_admin_trigger_gets_422_for_invalid_scope(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )

    async def _raise_invalid(*args, **kwargs):
        raise InvalidSyncRequest("Unknown group_external_id", path="group_external_id")

    monkeypatch.setattr(admin_router_module, "enqueue_manual_sync", _raise_invalid)

    response = TestClient(app).post(
        "/sync", json={"scope": "group", "group_external_id": "does-not-exist"}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "sync_request_invalid"


def test_platform_admin_trigger_succeeds_and_schedules_background_run(monkeypatch) -> None:
    from datetime import UTC, datetime

    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )
    scheduled: list[tuple] = []
    monkeypatch.setattr(
        admin_router_module,
        "run_manual_sync",
        lambda *args, **kwargs: scheduled.append((args, kwargs)),
    )

    request = ManualSyncRequest(
        id=7,
        bot_instance_id=1,
        installation_id=42,
        requested_by_admin_id=9,
        requested_at=datetime.now(tz=UTC),
        provider="miit_timetable",
        scope="all",
        group_external_id=None,
        status="queued",
    )

    async def _fake_enqueue(*args, **kwargs):
        return request, "Иванов И.И.", None, None

    monkeypatch.setattr(admin_router_module, "enqueue_manual_sync", _fake_enqueue)

    response = TestClient(app).post("/sync", json={"scope": "all"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 7
    assert body["status"] == "queued"
    assert body["requested_by_admin_name"] == "Иванов И.И."
    assert len(scheduled) == 1


def test_platform_admin_trigger_for_institute_scope_returns_institute_name(monkeypatch) -> None:
    from datetime import UTC, datetime

    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )
    monkeypatch.setattr(admin_router_module, "run_manual_sync", lambda *args, **kwargs: None)

    request = ManualSyncRequest(
        id=8,
        bot_instance_id=1,
        installation_id=42,
        requested_by_admin_id=9,
        requested_at=datetime.now(tz=UTC),
        provider="miit_timetable",
        scope="institute",
        group_external_id=None,
        institute_external_id="AGA",
        status="queued",
    )

    async def _fake_enqueue(*args, **kwargs):
        return request, "Иванов И.И.", None, "Академия гражданской авиации"

    monkeypatch.setattr(admin_router_module, "enqueue_manual_sync", _fake_enqueue)

    response = TestClient(app).post(
        "/sync", json={"scope": "institute", "institute_external_id": "AGA"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["institute_external_id"] == "AGA"
    assert body["institute_name"] == "Академия гражданской авиации"


def test_bot_admin_cannot_refresh_groups() -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_bot_admin_principal(), bot)

    response = TestClient(app).post("/refresh-groups")

    assert response.status_code == 403


def test_platform_admin_refresh_groups_succeeds(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )

    async def _fake_refresh(*args, **kwargs):
        return 9, 703

    monkeypatch.setattr(admin_router_module, "refresh_groups", _fake_refresh)

    response = TestClient(app).post("/refresh-groups")

    assert response.status_code == 200
    body = response.json()
    assert body == {"institutes_count": 9, "groups_count": 703}


def test_platform_admin_refresh_groups_gets_409_when_sync_already_running(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(_platform_admin_principal(), bot)
    monkeypatch.setattr(
        admin_router_module,
        "SqlAlchemyCapabilityInstallationRepository",
        lambda _db: type("Repo", (), {"get": lambda self, *a, **k: _installed_installation(1)})(),
    )

    async def _raise_already_running(*args, **kwargs):
        raise SyncAlreadyRunning(1)

    monkeypatch.setattr(admin_router_module, "refresh_groups", _raise_already_running)

    response = TestClient(app).post("/refresh-groups")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "sync_already_running"


# --- refresh_groups internals: navigation-tree cache invalidation (Task 046) ---
#
# `refresh_groups` is one of the two places `replace_hierarchy` is ever called (the other is the
# nightly `sync_installation`); both must invalidate the cached navigation tree right after a
# successful replace, and must not invalidate it when the replace never happened.


class _FakeRedisLock:
    def set(self, _key: str, _value: str, *, nx: bool, ex: int) -> bool:
        return True

    def delete(self, _key: str) -> None:
        pass


class _FakeTreeCache:
    def __init__(self) -> None:
        self.invalidate_calls = 0

    def invalidate(self) -> None:
        self.invalidate_calls += 1


class _RecordingRepository:
    """Stands in for `SqlAlchemyRutScheduleRepository(db)` -- `replace_hierarchy` is the only
    method `refresh_groups` calls on it."""

    instances: list["_RecordingRepository"] = []

    def __init__(self, _db) -> None:
        self.replace_hierarchy_calls: list[tuple] = []
        _RecordingRepository.instances.append(self)

    def replace_hierarchy(self, institutes, groups) -> None:
        self.replace_hierarchy_calls.append((institutes, groups))


class _FakeProvider:
    def __init__(self, hierarchy: ProviderHierarchy | None = None, error: Exception | None = None) -> None:
        self._hierarchy = hierarchy
        self._error = error

    async def read_hierarchy(self) -> ProviderHierarchy:
        if self._error is not None:
            raise self._error
        assert self._hierarchy is not None
        return self._hierarchy


def _fake_hierarchy() -> ProviderHierarchy:
    return ProviderHierarchy(
        institutes=(ProviderInstitute(external_id="ВГТ", name="Институт транспорта"),),
        groups=(
            ProviderGroup(
                external_id="1", name="ВГТ-111", institute_external_id="ВГТ", course_number=1
            ),
        ),
    )


def test_refresh_groups_invalidates_navigation_tree_cache_after_commit(monkeypatch) -> None:
    fake_cache = _FakeTreeCache()
    _RecordingRepository.instances = []
    monkeypatch.setattr(manual_sync_module, "redis_client", _FakeRedisLock())
    monkeypatch.setattr(manual_sync_module, "RedisScheduleTreeCache", lambda: fake_cache)
    monkeypatch.setattr(manual_sync_module, "SqlAlchemyRutScheduleRepository", _RecordingRepository)
    monkeypatch.setattr(
        manual_sync_module, "get_schedule_provider", lambda: _FakeProvider(hierarchy=_fake_hierarchy())
    )

    institutes_count, groups_count = asyncio.run(manual_sync_module.refresh_groups(_DummySession()))

    assert (institutes_count, groups_count) == (1, 1)
    assert fake_cache.invalidate_calls == 1
    assert len(_RecordingRepository.instances[0].replace_hierarchy_calls) == 1


def test_refresh_groups_does_not_invalidate_cache_when_provider_fails(monkeypatch) -> None:
    fake_cache = _FakeTreeCache()
    monkeypatch.setattr(manual_sync_module, "redis_client", _FakeRedisLock())
    monkeypatch.setattr(manual_sync_module, "RedisScheduleTreeCache", lambda: fake_cache)
    monkeypatch.setattr(manual_sync_module, "SqlAlchemyRutScheduleRepository", _RecordingRepository)
    monkeypatch.setattr(
        manual_sync_module,
        "get_schedule_provider",
        lambda: _FakeProvider(error=MiitTimetableProviderError("source unreachable")),
    )

    with pytest.raises(MiitTimetableProviderError):
        asyncio.run(manual_sync_module.refresh_groups(_DummySession()))

    assert fake_cache.invalidate_calls == 0
