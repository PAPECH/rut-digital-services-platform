from __future__ import annotations

import json
from datetime import UTC, datetime

from ..domain.entities import (
    GroupSchedule,
    NavigationCourse,
    NavigationInstitute,
    NavigationTree,
    ScheduleGroup,
    ScheduleLesson,
)
from ..domain.repositories import RutScheduleRepository
from .ports import ScheduleHierarchyProvider, ScheduleTreeCache


class GroupNotFound(LookupError):
    pass


class ScheduleNotYetSynced(RuntimeError):
    """Raised when a group has no cached schedule yet -- the nightly crawl (see
    infrastructure/sync_worker.py) hasn't reached it (freshly added group, or the very first
    night hasn't run). Never triggers a live fetch: the source site is only reachable once a
    night, so a request-time miss must surface as a defined, temporary failure instead."""

    pass


def _tree_to_payload(tree: NavigationTree) -> str:
    return json.dumps(
        {
            "institutes": [
                {
                    "external_id": institute.external_id,
                    "name": institute.name,
                    "courses": [
                        {
                            "course_number": course.course_number,
                            "groups": [
                                {
                                    "external_id": group.external_id,
                                    "name": group.name,
                                    "institute_external_id": group.institute_external_id,
                                    "course_number": group.course_number,
                                }
                                for group in course.groups
                            ],
                        }
                        for course in institute.courses
                    ],
                }
                for institute in tree.institutes
            ]
        }
    )


def _payload_to_tree(payload: str) -> NavigationTree:
    data = json.loads(payload)
    return NavigationTree(
        institutes=tuple(
            NavigationInstitute(
                external_id=institute["external_id"],
                name=institute["name"],
                courses=tuple(
                    NavigationCourse(
                        course_number=course["course_number"],
                        groups=tuple(
                            ScheduleGroup(
                                external_id=group["external_id"],
                                name=group["name"],
                                institute_external_id=group["institute_external_id"],
                                course_number=group["course_number"],
                            )
                            for group in course["groups"]
                        ),
                    )
                    for course in institute["courses"]
                ),
            )
            for institute in data["institutes"]
        )
    )


class GetNavigationTree:
    """Replaces `ListInstitutes`/`ListCourses`/`ListGroups` (Task 046): assembles the whole
    institutes->courses->groups catalog in one call instead of one request per drill-down step,
    cached read-through since it changes only when `replace_hierarchy` runs (nightly crawl or the
    platform-admin "refresh groups" action, both of which call the cache's `invalidate()` right
    after -- see infrastructure/sync_worker.py and infrastructure/manual_sync.py)."""

    def __init__(self, repository: RutScheduleRepository, cache: ScheduleTreeCache) -> None:
        self._repository = repository
        self._cache = cache

    def execute(self) -> NavigationTree:
        cached = self._cache.get()
        if cached is not None:
            try:
                return _payload_to_tree(cached)
            except (ValueError, KeyError, TypeError):
                pass  # corrupt/incompatible cache entry -- rebuild from Postgres below
        tree = self._build_tree()
        self._cache.set(_tree_to_payload(tree))
        return tree

    def _build_tree(self) -> NavigationTree:
        institutes = self._repository.list_institutes()
        groups_by_institute: dict[str, dict[int, list[ScheduleGroup]]] = {}
        for group in self._repository.list_all_groups():
            groups_by_institute.setdefault(group.institute_external_id, {}).setdefault(
                group.course_number, []
            ).append(group)
        return NavigationTree(
            institutes=tuple(
                NavigationInstitute(
                    external_id=institute.external_id,
                    name=institute.name,
                    courses=tuple(
                        NavigationCourse(course_number=course_number, groups=tuple(groups))
                        for course_number, groups in sorted(
                            groups_by_institute.get(institute.external_id, {}).items()
                        )
                    ),
                )
                for institute in institutes
            )
        )


class GetGroupSchedule:
    """Serves the latest nightly-synced snapshot only -- see infrastructure/sync_worker.py's
    eager nightly crawl of every group. This use case must never fetch the source site live on a
    user's request: the site is only reachable once a night, around 02:00 Moscow time, so a
    request for a group nothing has synced yet raises ScheduleNotYetSynced rather than reaching
    out live."""

    # A very large bound rather than an actual TTL: freshness is now guaranteed by the nightly
    # crawl's cadence, not by per-request expiry -- this just means "return whatever was last
    # synced, however old."
    _NO_AGE_LIMIT_SECONDS = 10 * 365 * 24 * 60 * 60

    def __init__(self, repository: RutScheduleRepository) -> None:
        self._repository = repository

    def execute(self, group_external_id: str) -> GroupSchedule:
        group = self._repository.get_group(group_external_id)
        if group is None:
            raise GroupNotFound(group_external_id)
        cached = self._repository.get_cached_schedule(group_external_id, self._NO_AGE_LIMIT_SECONDS)
        if cached is None:
            raise ScheduleNotYetSynced(group_external_id)
        return cached


class SyncGroupSchedule:
    """Fetches one group's lessons from the provider and stores them -- the unit of work the
    nightly crawl (infrastructure/sync_worker.py) repeats for every group. Not reachable from any
    user-facing request path; only the worker calls this, once a night."""

    def __init__(self, repository: RutScheduleRepository, provider: ScheduleHierarchyProvider) -> None:
        self._repository = repository
        self._provider = provider

    async def execute(self, group_external_id: str) -> None:
        result = await self._provider.read_group_lessons(group_external_id)
        lessons = [
            ScheduleLesson(
                weekday=item.weekday,
                week_parity=item.week_parity,
                period_label=item.period_label,
                start_time=item.start_time,
                end_time=item.end_time,
                lesson_kind=item.lesson_kind,
                discipline=item.discipline,
                room=item.room,
                teachers=item.teachers,
                combined_groups=item.combined_groups,
                lesson_date=item.lesson_date,
            )
            for item in result.lessons
        ]
        self._repository.save_schedule(
            group_external_id,
            lessons,
            datetime.now(tz=UTC),
            result.semester_start,
            result.semester_end,
        )
