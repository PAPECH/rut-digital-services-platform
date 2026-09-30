from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class ScheduleInstitute:
    external_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ScheduleGroup:
    external_id: str
    name: str
    institute_external_id: str
    course_number: int


@dataclass(frozen=True, slots=True)
class ScheduleLesson:
    weekday: int
    week_parity: int
    period_label: str
    start_time: str
    end_time: str
    lesson_kind: str
    discipline: str
    room: str | None
    teachers: str | None
    combined_groups: str | None
    # Reserved for the future Oracle provider's `schedule_.idk_periodicity` value (see
    # "Расписание группы для бота.sql"). The HTML scraper has no equivalent signal — it only
    # knows which week-parity tab a lesson came from — so this stays unset until
    # OracleScheduleProvider exists. Deliberately not derived or used by any UI logic yet.
    periodicity_code: int | None = None
    # Set only for a "Разовое" (one-off, explicitly dated) session — see ProviderLesson.
    # `week_parity` is meaningless whenever this is set; callers must match on this date
    # directly instead of weekday/week_parity when it's present.
    lesson_date: date | None = None


@dataclass(frozen=True, slots=True)
class GroupSchedule:
    group: ScheduleGroup
    lessons: tuple[ScheduleLesson, ...]
    synced_at: datetime
    # The academic term's date range -- the anchor a client needs to map "today" to week_parity
    # 1/2. None when the source page didn't expose it (parse miss); callers must degrade
    # gracefully, not assume it's always present.
    semester_start: date | None
    semester_end: date | None


@dataclass(frozen=True, slots=True)
class NavigationCourse:
    course_number: int
    groups: tuple[ScheduleGroup, ...]


@dataclass(frozen=True, slots=True)
class NavigationInstitute:
    external_id: str
    name: str
    courses: tuple[NavigationCourse, ...]


@dataclass(frozen=True, slots=True)
class NavigationTree:
    """The whole institutes->courses->groups catalog, assembled and cached as one unit (Task 046)
    -- replaces the old institute/course/group drill-down that issued one request per step."""

    institutes: tuple[NavigationInstitute, ...]


@dataclass(frozen=True, slots=True)
class GroupWithLastSync:
    """One row of the platform-admin "groups with last sync" table (Task 045) -- every group known
    to the installation's hierarchy cache, joined with when its lessons were last synced (null for
    a group the nightly crawl hasn't reached yet)."""

    group: ScheduleGroup
    last_synced_at: datetime | None


# Manual-sync-request status values, in the order a request actually moves through them (a
# terminal status is exactly one of the last three).
ManualSyncStatus = str  # "queued" | "running" | "succeeded" | "failed" | "partial"


@dataclass(frozen=True, slots=True)
class ManualSyncRequest:
    """One admin-triggered manual sync (Task 045) -- distinct from the nightly cron, which never
    creates a row here. `requested_by_admin_id` is null once the admin account is deleted
    (`ON DELETE SET NULL`); the historical row itself is never removed."""

    id: int | None
    bot_instance_id: int
    installation_id: int
    requested_by_admin_id: int | None
    requested_at: datetime
    provider: str
    scope: str  # "group" | "institute" | "all"
    group_external_id: str | None
    status: ManualSyncStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    groups_synced: int | None = None
    groups_failed: int | None = None
    error_code: str | None = None
    # Set only for scope="institute" -- mutually exclusive with group_external_id.
    institute_external_id: str | None = None
