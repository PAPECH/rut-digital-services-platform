from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.modules.capabilities.domain.entities import CapabilityInstallation
from app.modules.capabilities.rut_schedule.application.ports import ProviderHierarchy
from app.modules.capabilities.rut_schedule.infrastructure import sync_worker as sync_worker_module

# `sync_installation` (the nightly crawl) is one of the two places `replace_hierarchy` is ever
# called (the other is `refresh_groups`, covered in test_rut_schedule_manual_sync.py); it must
# invalidate the cached navigation tree right after a successful replace (Task 046). Every
# collaborator besides the cache/lock under test is faked out -- `sync_installation` otherwise
# needs a real Postgres session, matching how this module is exercised nowhere else today.


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSessionCtx:
    def __init__(self, record: object) -> None:
        self._record = record

    def __enter__(self) -> "_FakeSessionCtx":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, _stmt: object) -> _ScalarResult:
        return _ScalarResult(self._record)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class _FakeInstallationRecord:
    def __init__(self, *, id: int, bot_instance_id: int, config: dict) -> None:
        self.id = id
        self.bot_instance_id = bot_instance_id
        self.config = config


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
    """Stands in for `SqlAlchemyRutScheduleRepository(db)`."""

    instances: list["_RecordingRepository"] = []

    def __init__(self, _db: object) -> None:
        self.replace_hierarchy_calls: list[tuple] = []
        _RecordingRepository.instances.append(self)

    def hierarchy_last_synced_at(self) -> datetime | None:
        return None  # never synced -- should_poll must return True

    def replace_hierarchy(self, institutes: object, groups: object) -> None:
        self.replace_hierarchy_calls.append((institutes, groups))


class _FakeInstallationRepo:
    def __init__(self, _db: object) -> None:
        pass

    def get(self, bot_instance_id: int, capability_key: str) -> CapabilityInstallation:
        return CapabilityInstallation(
            id=1,
            bot_instance_id=bot_instance_id,
            capability_key=capability_key,
            is_enabled=True,
            config={},
            config_revision=1,
        )

    def save(self, _installation: CapabilityInstallation) -> None:
        pass


class _FakeProvider:
    async def read_hierarchy(self) -> ProviderHierarchy:
        # No groups -- keeps `crawl_all_groups` (called after the invalidation under test) a no-op.
        return ProviderHierarchy(institutes=(), groups=())

    async def probe(self) -> None:
        pass


def _config() -> dict:
    return {
        "provider": "miit_timetable",
        "title": "Расписание",
        "subtitle": "sub",
        "group_cache_ttl_seconds": 900,
        "hierarchy_sync_interval_seconds": 21_600,
        "night_auto_sync_enabled": True,
    }


def test_sync_installation_invalidates_navigation_tree_cache_after_hierarchy_replace(monkeypatch) -> None:
    record = _FakeInstallationRecord(id=1, bot_instance_id=1, config=_config())
    fake_cache = _FakeTreeCache()
    _RecordingRepository.instances = []

    monkeypatch.setattr(sync_worker_module, "SessionLocal", lambda: _FakeSessionCtx(record))
    monkeypatch.setattr(sync_worker_module, "redis_client", _FakeRedisLock())
    monkeypatch.setattr(sync_worker_module, "RedisScheduleTreeCache", lambda: fake_cache)
    monkeypatch.setattr(sync_worker_module, "SqlAlchemyRutScheduleRepository", _RecordingRepository)
    monkeypatch.setattr(
        sync_worker_module, "SqlAlchemyCapabilityInstallationRepository", _FakeInstallationRepo
    )
    monkeypatch.setattr(sync_worker_module, "get_schedule_provider", lambda: _FakeProvider())

    asyncio.run(sync_worker_module.sync_installation(1))

    assert fake_cache.invalidate_calls == 1
    assert len(_RecordingRepository.instances[-1].replace_hierarchy_calls) == 1


def test_sync_installation_skips_entirely_when_night_auto_sync_disabled(monkeypatch) -> None:
    config = _config()
    config["night_auto_sync_enabled"] = False
    record = _FakeInstallationRecord(id=1, bot_instance_id=1, config=config)
    fake_cache = _FakeTreeCache()
    _RecordingRepository.instances = []

    monkeypatch.setattr(sync_worker_module, "SessionLocal", lambda: _FakeSessionCtx(record))
    monkeypatch.setattr(sync_worker_module, "redis_client", _FakeRedisLock())
    monkeypatch.setattr(sync_worker_module, "RedisScheduleTreeCache", lambda: fake_cache)
    monkeypatch.setattr(sync_worker_module, "SqlAlchemyRutScheduleRepository", _RecordingRepository)

    asyncio.run(sync_worker_module.sync_installation(1))

    assert fake_cache.invalidate_calls == 0
    assert _RecordingRepository.instances == []
