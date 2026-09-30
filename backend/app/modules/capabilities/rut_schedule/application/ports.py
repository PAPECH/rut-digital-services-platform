from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ProviderInstitute:
    external_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ProviderGroup:
    external_id: str
    name: str
    institute_external_id: str
    course_number: int


@dataclass(frozen=True, slots=True)
class ProviderLesson:
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
    # Set only for a "Разовое" (one-off, explicitly dated) session -- see
    # MiitTimetableProvider's `window._timetableData` branch. `week_parity` is meaningless
    # whenever this is set (these pages have no "II неделя" concept at all); consumers must
    # match on this date directly instead of weekday/week_parity when it's present.
    lesson_date: date | None = None


@dataclass(frozen=True, slots=True)
class ProviderHierarchy:
    institutes: tuple[ProviderInstitute, ...]
    groups: tuple[ProviderGroup, ...]


@dataclass(frozen=True, slots=True)
class ProviderGroupLessons:
    lessons: tuple[ProviderLesson, ...]
    # The academic term's date range, scraped from the same group page (e.g. "Расписание
    # действует с 01.09.2026 по 04.01.2027"). This is the anchor that lets a specific calendar
    # date be mapped to week_parity 1/2 -- the site itself only labels lessons "I неделя"/"II
    # неделя", not by date, so without this anchor a client could never say "which week is today."
    semester_start: date | None
    semester_end: date | None


class ScheduleHierarchyProvider(Protocol):
    async def read_hierarchy(self) -> ProviderHierarchy: ...

    async def read_group_lessons(self, group_external_id: str) -> ProviderGroupLessons: ...

    async def probe(self) -> None: ...


class ScheduleTreeCache(Protocol):
    """Caches the assembled navigation-tree JSON payload (Task 046). Implementations must never
    raise -- a cache failure degrades to a miss (`get` returns None) or a no-op (`set`/
    `invalidate`), never a request failure; see `infrastructure/tree_cache.py`."""

    def get(self) -> str | None: ...

    def set(self, payload: str) -> None: ...

    def invalidate(self) -> None: ...


class SyncEventBroadcaster(Protocol):
    """Pushes a manual-sync status update to whatever admin sockets are watching a bot's
    platform-admin room (Task 045). A Protocol here, not a direct import of the concrete
    `ws_hub`-backed adapter, keeps this application-layer use case independent of the WebSocket
    infrastructure detail -- the router wires the real adapter in
    `infrastructure/ws_broadcaster.py`."""

    async def broadcast(self, bot_instance_id: int, event: dict[str, Any]) -> None: ...
