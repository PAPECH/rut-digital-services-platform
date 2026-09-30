from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import CurrentPrincipal, get_current_principal, require_student
from app.core.errors import service_unavailable
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.capabilities.domain.entities import CapabilityInstallation
from app.modules.capabilities.rut_schedule.domain.entities import ScheduleGroup, ScheduleInstitute
from app.modules.capabilities.rut_schedule.presentation import router as router_module
from app.modules.maintenance.presentation.dependencies import enforce_user_access_available
from app.modules.tenancy.presentation.dependencies import require_tenant_access

# The public router's institutes/courses/groups drill-down (`/institutes`,
# `/institutes/{id}/courses`, `/institutes/{id}/courses/{n}/groups`) was replaced by
# `/navigation-tree` (Task 046) -- this file covers the new endpoint's HTTP contract; DB/Redis
# collaborators are faked exactly as `test_rut_schedule_manual_sync.py` fakes the admin router's.


class _NoRowResult:
    def scalar_one_or_none(self) -> None:
        return None


class _DummySession:
    """`.execute` only needs to satisfy `enforce_user_access_available`'s maintenance-policy
    lookup (`SqlAlchemyMaintenanceRepository.get`, called twice: global + per-bot scope) --
    everything else this test drives (the capability/schedule repositories) is faked out
    separately via `router_module` monkeypatches."""

    def execute(self, _statement: object) -> _NoRowResult:
        return _NoRowResult()


def _principal(bot_id: int) -> CurrentPrincipal:
    return CurrentPrincipal("u:7", "student", "max", 7, None, bot_id, f"bot-{bot_id}")


def _rut_schedule_config() -> dict:
    return {
        "provider": "miit_timetable",
        "title": "Расписание",
        "subtitle": "sub",
        "group_cache_ttl_seconds": 900,
        "hierarchy_sync_interval_seconds": 21_600,
        "night_auto_sync_enabled": True,
    }


class _FakeInstallationRepo:
    def __init__(self, _db: object) -> None:
        pass

    def get(self, bot_instance_id: int, capability_key: str) -> CapabilityInstallation:
        return CapabilityInstallation(
            id=1,
            bot_instance_id=bot_instance_id,
            capability_key=capability_key,
            is_enabled=True,
            config=_rut_schedule_config(),
            config_revision=1,
        )


class _DisabledInstallationRepo:
    def __init__(self, _db: object) -> None:
        pass

    def get(self, _bot_instance_id: int, _capability_key: str) -> None:
        return None


class _FakeScheduleRepository:
    def __init__(self, _db: object) -> None:
        pass

    def list_institutes(self) -> list[ScheduleInstitute]:
        return [ScheduleInstitute(external_id="ВГТ", name="Институт транспорта")]

    def list_all_groups(self) -> list[ScheduleGroup]:
        return [
            ScheduleGroup(external_id="1", name="ВГТ-111", institute_external_id="ВГТ", course_number=1),
            ScheduleGroup(external_id="2", name="ВГТ-211", institute_external_id="ВГТ", course_number=2),
        ]


class _FakeTreeCache:
    def get(self) -> str | None:
        return None

    def set(self, _payload: str) -> None:
        pass

    def invalidate(self) -> None:
        pass


def _app(bot: BotInstance, principal: CurrentPrincipal, monkeypatch) -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router, prefix="/capabilities/rut-schedule")
    app.dependency_overrides[require_student] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[get_db] = lambda: _DummySession()
    monkeypatch.setattr(router_module, "SqlAlchemyCapabilityInstallationRepository", _FakeInstallationRepo)
    monkeypatch.setattr(router_module, "SqlAlchemyRutScheduleRepository", _FakeScheduleRepository)
    monkeypatch.setattr(router_module, "RedisScheduleTreeCache", _FakeTreeCache)
    return app


def test_navigation_tree_returns_institutes_grouped_by_course(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(bot, _principal(1), monkeypatch)

    response = TestClient(app).get("/capabilities/rut-schedule/navigation-tree")

    assert response.status_code == 200
    assert response.json() == {
        "institutes": [
            {
                "external_id": "ВГТ",
                "name": "Институт транспорта",
                "courses": [
                    {
                        "course_number": 1,
                        "groups": [
                            {
                                "external_id": "1",
                                "name": "ВГТ-111",
                                "institute_external_id": "ВГТ",
                                "course_number": 1,
                            }
                        ],
                    },
                    {
                        "course_number": 2,
                        "groups": [
                            {
                                "external_id": "2",
                                "name": "ВГТ-211",
                                "institute_external_id": "ВГТ",
                                "course_number": 2,
                            }
                        ],
                    },
                ],
            }
        ]
    }


def test_navigation_tree_blocked_in_full_stop_maintenance(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(bot, _principal(1), monkeypatch)

    def blocked() -> None:
        raise service_unavailable("Технические работы", code="maintenance_mode", mode="full_stop")

    app.dependency_overrides[enforce_user_access_available] = blocked

    response = TestClient(app).get("/capabilities/rut-schedule/navigation-tree")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "maintenance_mode"


def test_navigation_tree_requires_capability_enabled(monkeypatch) -> None:
    bot = BotInstance(id=1, slug="bot-1", name="Первый бот")
    app = _app(bot, _principal(1), monkeypatch)
    monkeypatch.setattr(router_module, "SqlAlchemyCapabilityInstallationRepository", _DisabledInstallationRepo)

    response = TestClient(app).get("/capabilities/rut-schedule/navigation-tree")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "capability_disabled"


def test_navigation_tree_rejects_user_token_bound_to_another_bot() -> None:
    app = FastAPI()
    app.include_router(router_module.router, prefix="/capabilities/rut-schedule")
    selected_bot = BotInstance(id=2, slug="bot-2", name="Второй бот")
    principal = _principal(1)
    app.dependency_overrides[require_tenant_access] = lambda: require_tenant_access(
        bot=selected_bot, principal=principal, db=None
    )
    app.dependency_overrides[get_db] = lambda: _DummySession()

    response = TestClient(app).get("/capabilities/rut-schedule/navigation-tree")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "tenant_mismatch"
