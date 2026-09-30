from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from .entities import (
    GroupSchedule,
    GroupWithLastSync,
    ManualSyncRequest,
    ScheduleGroup,
    ScheduleInstitute,
    ScheduleLesson,
)


class RutScheduleRepository(Protocol):
    """The institute/group/lesson catalog is platform-wide (see infrastructure/models.py) -- no
    method here is scoped by `bot_instance_id`/`installation_id`."""

    def list_institutes(self) -> list[ScheduleInstitute]: ...

    def hierarchy_last_synced_at(self) -> datetime | None: ...

    def get_group(self, group_external_id: str) -> ScheduleGroup | None: ...

    def list_all_groups(self) -> list[ScheduleGroup]: ...

    def list_groups_by_institute(self, institute_external_id: str) -> list[ScheduleGroup]: ...

    def list_groups_with_last_sync(self, *, limit: int, offset: int) -> list[GroupWithLastSync]: ...

    def get_cached_schedule(
        self, group_external_id: str, max_age_seconds: int
    ) -> GroupSchedule | None: ...

    def save_schedule(
        self,
        group_external_id: str,
        lessons: list[ScheduleLesson],
        synced_at: datetime,
        semester_start: date | None,
        semester_end: date | None,
    ) -> None: ...

    def replace_hierarchy(
        self,
        institutes: list[ScheduleInstitute],
        groups: list[ScheduleGroup],
    ) -> None: ...


class RutScheduleSyncLogRepository(Protocol):
    """Owns only the platform-admin manual-sync-request log (Task 045) -- kept separate from
    `RutScheduleRepository` (hierarchy/lessons) since it's a distinct read/write path with its own
    table, not another view over the existing cache. The log itself is platform-wide too (see
    infrastructure/models.py) -- `create()` still records `bot_instance_id`/`installation_id` as
    informational context (which bot's panel triggered this), but `list_recent()` is not filtered
    by them; every platform admin, on any bot, sees the same global log."""

    def create(
        self,
        *,
        bot_instance_id: int,
        installation_id: int,
        requested_by_admin_id: int | None,
        provider: str,
        scope: str,
        group_external_id: str | None,
        institute_external_id: str | None = None,
    ) -> ManualSyncRequest: ...

    def mark_running(self, request_id: int, *, started_at: datetime) -> ManualSyncRequest: ...

    def mark_finished(
        self,
        request_id: int,
        *,
        status: str,
        finished_at: datetime,
        groups_synced: int | None = None,
        groups_failed: int | None = None,
        error_code: str | None = None,
    ) -> ManualSyncRequest: ...

    def list_recent(
        self, limit: int
    ) -> list[tuple[ManualSyncRequest, str | None, str | None, str | None]]:
        """Returns (request, requesting_admin_name, group_name, institute_name) tuples, newest
        first -- all three names are resolved here (outer joins against
        `admins`/`rut_schedule_groups`/`rut_schedule_institutes`) rather than by the caller,
        matching how `api/routes/audit.py` already resolves `AuditLog.admin_id` to a display name.
        `group_name`/`institute_name` are null unless the matching scope was used, or if the
        group/institute was since removed from the hierarchy cache."""
        ...
