from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

import pytest

from app.modules.capabilities.rut_schedule.application.ports import (
    ProviderGroupLessons,
    ProviderLesson,
)
from app.modules.capabilities.rut_schedule.application.use_cases import (
    GetGroupSchedule,
    GetNavigationTree,
    GroupNotFound,
    ScheduleNotYetSynced,
    SyncGroupSchedule,
)
from app.modules.capabilities.rut_schedule.domain.entities import (
    GroupSchedule,
    ScheduleGroup,
    ScheduleInstitute,
)
from app.modules.capabilities.rut_schedule.infrastructure.sync_worker import (
    NIGHTLY_SYNC_HOUR_UTC,
    NIGHTLY_SYNC_MINUTE_UTC,
    schedule_jobs,
)


class InMemoryRutScheduleRepository:
    """The institute/group/lesson catalog is platform-wide (Task 045's "Follow-up, 2026-09-02"),
    so none of these methods take bot_instance_id/installation_id -- matching
    RutScheduleRepository's real signature."""

    def __init__(self) -> None:
        self.institutes: dict[str, ScheduleInstitute] = {}
        self.groups: dict[str, ScheduleGroup] = {}
        self.schedules: dict[str, GroupSchedule] = {}

    def add_institute(self, institute: ScheduleInstitute) -> None:
        self.institutes[institute.external_id] = institute

    def add_group(self, group: ScheduleGroup) -> None:
        self.groups[group.external_id] = group

    def list_institutes(self):
        return sorted(self.institutes.values(), key=lambda i: i.name)

    def list_all_groups(self):
        return sorted(self.groups.values(), key=lambda g: g.name)

    def get_group(self, group_external_id):
        return self.groups.get(group_external_id)

    def get_cached_schedule(self, group_external_id, max_age_seconds):
        return self.schedules.get(group_external_id)

    def save_schedule(
        self,
        group_external_id,
        lessons,
        synced_at,
        semester_start,
        semester_end,
    ) -> None:
        group = self.groups[group_external_id]
        self.schedules[group_external_id] = GroupSchedule(
            group=group,
            lessons=tuple(lessons),
            synced_at=synced_at,
            semester_start=semester_start,
            semester_end=semester_end,
        )


class FakeProvider:
    def __init__(self, lessons_by_group: dict[str, ProviderGroupLessons]) -> None:
        self._lessons_by_group = lessons_by_group
        self.requested: list[str] = []

    async def read_hierarchy(self):
        raise NotImplementedError

    async def read_group_lessons(self, group_external_id: str) -> ProviderGroupLessons:
        self.requested.append(group_external_id)
        return self._lessons_by_group[group_external_id]

    async def probe(self) -> None:
        pass


def _group(external_id: str = "215959") -> ScheduleGroup:
    return ScheduleGroup(
        external_id=external_id, name="ВГТ-111", institute_external_id="ВГТ", course_number=1
    )


def test_get_group_schedule_raises_group_not_found_for_unknown_group() -> None:
    repository = InMemoryRutScheduleRepository()
    with pytest.raises(GroupNotFound):
        GetGroupSchedule(repository).execute("missing")


def test_get_group_schedule_never_fetches_live_and_reports_not_yet_synced() -> None:
    """The source site is only reachable from the nightly worker -- a group with nothing cached
    yet must be a defined failure, not trigger a live per-request fetch."""
    repository = InMemoryRutScheduleRepository()
    repository.add_group(_group())

    with pytest.raises(ScheduleNotYetSynced):
        GetGroupSchedule(repository).execute("215959")


def test_get_group_schedule_returns_whatever_was_last_synced_regardless_of_age() -> None:
    repository = InMemoryRutScheduleRepository()
    group = _group()
    repository.add_group(group)
    stale_sync = datetime(2020, 1, 1, tzinfo=UTC)
    repository.schedules[group.external_id] = GroupSchedule(
        group=group, lessons=(), synced_at=stale_sync, semester_start=None, semester_end=None
    )

    result = GetGroupSchedule(repository).execute(group.external_id)

    assert result.synced_at == stale_sync


def test_sync_group_schedule_fetches_from_provider_and_saves() -> None:
    repository = InMemoryRutScheduleRepository()
    group = _group()
    repository.add_group(group)
    lessons = ProviderGroupLessons(
        lessons=(
            ProviderLesson(
                weekday=1,
                week_parity=1,
                period_label="1 пара",
                start_time="09:00",
                end_time="10:30",
                lesson_kind="лекция",
                discipline="Математика",
                room="101",
                teachers="Иванов И.И.",
                combined_groups=None,
            ),
        ),
        semester_start=None,
        semester_end=None,
    )
    provider = FakeProvider({group.external_id: lessons})

    asyncio.run(SyncGroupSchedule(repository, provider).execute(group.external_id))

    saved = repository.schedules[group.external_id]
    assert saved.lessons[0].discipline == "Математика"
    assert provider.requested == [group.external_id]

    # And now GetGroupSchedule can serve it without touching the provider again.
    served = GetGroupSchedule(repository).execute(group.external_id)
    assert served.lessons == saved.lessons


def test_sync_group_schedule_preserves_lesson_date_for_dated_sessions() -> None:
    """A "Разовое" (type=2) group's lessons carry an explicit lesson_date from the provider --
    this must survive the round trip through SyncGroupSchedule into the stored ScheduleLesson
    unchanged. See docs/tasks/043-rut-schedule-capability.md, "Addendum, 2026-09-02"."""
    repository = InMemoryRutScheduleRepository()
    group = _group("216161")
    repository.add_group(group)
    lessons = ProviderGroupLessons(
        lessons=(
            ProviderLesson(
                weekday=3,
                week_parity=1,
                period_label="",
                start_time="18:30",
                end_time="19:50",
                lesson_kind="Лекция",
                discipline="Высокоскоростной транспорт",
                room="ГУК-8, 8516",
                teachers="Корнетова Мария Павловна",
                combined_groups="ПСП-171",
                lesson_date=date(2026, 9, 2),
            ),
        ),
        semester_start=None,
        semester_end=None,
    )
    provider = FakeProvider({group.external_id: lessons})

    asyncio.run(SyncGroupSchedule(repository, provider).execute(group.external_id))

    saved = repository.schedules[group.external_id]
    assert saved.lessons[0].lesson_date == date(2026, 9, 2)


class FakeScheduleTreeCache:
    def __init__(self, seeded: str | None = None) -> None:
        self.payload = seeded
        self.get_calls = 0
        self.set_calls = 0

    def get(self) -> str | None:
        self.get_calls += 1
        return self.payload

    def set(self, payload: str) -> None:
        self.set_calls += 1
        self.payload = payload

    def invalidate(self) -> None:
        self.payload = None


def _institute(external_id: str = "ВГТ", name: str = "Институт транспорта") -> ScheduleInstitute:
    return ScheduleInstitute(external_id=external_id, name=name)


def test_get_navigation_tree_builds_from_repository_on_cache_miss() -> None:
    repository = InMemoryRutScheduleRepository()
    repository.add_institute(_institute())
    repository.add_group(_group())
    cache = FakeScheduleTreeCache()

    tree = GetNavigationTree(repository, cache).execute()

    assert len(tree.institutes) == 1
    institute = tree.institutes[0]
    assert institute.external_id == "ВГТ"
    assert len(institute.courses) == 1
    assert institute.courses[0].course_number == 1
    assert institute.courses[0].groups[0].external_id == "215959"
    # A miss populates the cache for the next read.
    assert cache.set_calls == 1


def test_get_navigation_tree_serves_from_cache_without_touching_repository() -> None:
    repository = InMemoryRutScheduleRepository()
    repository.add_institute(_institute())
    repository.add_group(_group())
    warm_cache = FakeScheduleTreeCache()
    seeded = GetNavigationTree(repository, warm_cache).execute()
    assert warm_cache.payload is not None

    # A second cache, seeded with the same payload but backed by a repository that would raise if
    # touched, proves the hit path never calls into the repository.
    class _ExplodingRepository:
        def list_institutes(self):
            raise AssertionError("must not be called on a cache hit")

        def list_all_groups(self):
            raise AssertionError("must not be called on a cache hit")

    hot_cache = FakeScheduleTreeCache(seeded=warm_cache.payload)
    result = GetNavigationTree(_ExplodingRepository(), hot_cache).execute()

    assert result == seeded
    assert hot_cache.set_calls == 0


def test_get_navigation_tree_rebuilds_on_corrupt_cache_payload() -> None:
    repository = InMemoryRutScheduleRepository()
    repository.add_institute(_institute())
    repository.add_group(_group())
    cache = FakeScheduleTreeCache(seeded="not valid json")

    tree = GetNavigationTree(repository, cache).execute()

    assert len(tree.institutes) == 1
    assert cache.set_calls == 1


def test_get_navigation_tree_groups_courses_correctly_across_multiple_institutes() -> None:
    repository = InMemoryRutScheduleRepository()
    repository.add_institute(_institute("ВГТ", "Институт транспорта"))
    repository.add_institute(_institute("ИЭФ", "Экономический факультет"))
    repository.add_group(
        ScheduleGroup(external_id="1", name="ВГТ-111", institute_external_id="ВГТ", course_number=1)
    )
    repository.add_group(
        ScheduleGroup(external_id="2", name="ВГТ-211", institute_external_id="ВГТ", course_number=2)
    )
    repository.add_group(
        ScheduleGroup(external_id="3", name="ИЭФ-111", institute_external_id="ИЭФ", course_number=1)
    )

    tree = GetNavigationTree(repository, FakeScheduleTreeCache()).execute()

    by_id = {institute.external_id: institute for institute in tree.institutes}
    assert [c.course_number for c in by_id["ВГТ"].courses] == [1, 2]
    assert [c.course_number for c in by_id["ИЭФ"].courses] == [1]
    assert by_id["ИЭФ"].courses[0].groups[0].external_id == "3"


class _RecordingScheduler:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def add_job(self, func, trigger, **kwargs):
        self.calls.append({"func": func, "trigger": trigger, **kwargs})


def test_nightly_job_is_a_fixed_cron_time_not_an_interval_with_immediate_run() -> None:
    """Regression test for the incident this was built to prevent: an `interval` trigger with
    `next_run_time=now()` fires immediately on every worker start/restart, which can hit the
    source site during the day. The job must be a fixed nightly cron time with no immediate
    `next_run_time` override."""
    scheduler = _RecordingScheduler()

    schedule_jobs(scheduler)

    assert len(scheduler.calls) == 1
    call = scheduler.calls[0]
    assert call["trigger"] == "cron"
    assert call["hour"] == NIGHTLY_SYNC_HOUR_UTC == 23
    assert call["minute"] == NIGHTLY_SYNC_MINUTE_UTC == 0
    assert "next_run_time" not in call
