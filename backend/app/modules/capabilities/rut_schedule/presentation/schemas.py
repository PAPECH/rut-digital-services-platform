from typing import Literal

from pydantic import BaseModel


class InstituteResponse(BaseModel):
    external_id: str
    name: str


class GroupResponse(BaseModel):
    external_id: str
    name: str
    institute_external_id: str
    course_number: int


class NavigationCourseResponse(BaseModel):
    course_number: int
    groups: list[GroupResponse]


class NavigationInstituteResponse(BaseModel):
    external_id: str
    name: str
    courses: list[NavigationCourseResponse]


class NavigationTreeResponse(BaseModel):
    institutes: list[NavigationInstituteResponse]


class LessonResponse(BaseModel):
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
    # Reserved for the future Oracle provider; always null from the current scraper-backed
    # provider. See ScheduleLesson.periodicity_code — deliberately not used by any UI logic yet.
    periodicity_code: int | None
    # ISO date string ("YYYY-MM-DD"), set only for a "Разовое" (one-off, explicitly dated)
    # session. `week_parity` is meaningless whenever this is set — clients must match on this
    # date directly instead of weekday/week_parity when it's present.
    lesson_date: str | None


class GroupScheduleResponse(BaseModel):
    group: GroupResponse
    lessons: list[LessonResponse]
    synced_at: str
    # ISO date strings ("YYYY-MM-DD"), or null if the source page didn't expose them (parse miss)
    # -- the anchor a client needs to map a calendar date to week_parity 1/2.
    semester_start: str | None
    semester_end: str | None


# --- Platform-admin manual sync controls (Task 045) ---


class ManualSyncTriggerRequest(BaseModel):
    scope: Literal["group", "institute", "all"]
    group_external_id: str | None = None
    institute_external_id: str | None = None


class ManualSyncRequestResponse(BaseModel):
    id: int
    requested_at: str
    requested_by_admin_id: int | None
    # Resolved server-side (outer join against `admins`), matching AuditPage's own convention --
    # the frontend shows "Сотрудник #<id>" only when this is null (a deleted admin account).
    requested_by_admin_name: str | None
    provider: str
    scope: str
    group_external_id: str | None
    group_name: str | None
    institute_external_id: str | None
    institute_name: str | None
    status: str
    started_at: str | None
    finished_at: str | None
    groups_synced: int | None
    groups_failed: int | None
    error_code: str | None


class GroupWithLastSyncResponse(BaseModel):
    group: GroupResponse
    last_synced_at: str | None


class RefreshGroupsResponse(BaseModel):
    institutes_count: int
    groups_count: int
