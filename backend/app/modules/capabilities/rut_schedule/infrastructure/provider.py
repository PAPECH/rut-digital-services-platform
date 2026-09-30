from __future__ import annotations

import asyncio
import json
import re
from datetime import date

import httpx

from ..application.ports import (
    ProviderGroup,
    ProviderGroupLessons,
    ProviderHierarchy,
    ProviderInstitute,
    ProviderLesson,
)

_BASE_URL = "https://miit.ru"
_MAX_RESPONSE_BYTES = 8_000_000
_RETRY_DELAYS = (0.0, 0.5, 1.5)
_USER_AGENT = "RUT-MAX-Platform/1.0 (+schedule sync; contact: platform administrator)"

_WEEKDAYS = {
    "понедельник": 1,
    "вторник": 2,
    "среда": 3,
    "четверг": 4,
    "пятница": 5,
    "суббота": 6,
    "воскресенье": 7,
}

# Hierarchy page (`/timetable`): institutes are announced by an inline script call carrying their
# abbreviation and full name; groups sit under "N курс" headings inside each institute's section,
# either as plain links or nested one level inside a per-specialty dropdown — both shapes reduce to
# the same `<a href="/timetable/{id}" ...>{name}</a>` fragment.
#
# One real institute ("ПИШ "Академия ВСМ"") ships an announcement with unescaped quotes baked into
# both arguments by the source site itself, e.g.:
#   addToPageContent("ПИШ-"Академия-ВСМ"", "Передовая инженерная школа «Академия ВСМ» (ПИШ "Академия
#   ВСМ")");
# A single `[^"]+`-per-argument regex can't match that at all, and since institute boundaries are
# derived from match positions, a skipped match doesn't just drop the institute -- it silently folds
# its entire course/group section into the *previous* institute's chunk (verified against the live
# page: the previous institute reported 16 groups that aren't its own). Parsing is split into two
# steps to fix this instead of one: first isolate each whole `addToPageContent(...);` call (safe --
# no real institute name contains the literal substring `);`, and requiring the call to open with a
# quote excludes the unrelated `function addToPageContent(id, display) { ... }` definition earlier
# on the page), then, only within that isolated span, greedily extract the two arguments anchored to
# the closing `");` at the very end of that same span. Greedy backtracking lands on the true
# (rightmost) boundary even with stray quotes earlier in the value, and staying confined to one
# isolated span keeps it from ever spanning into a neighboring institute's announcement.
_INSTITUTE_CALL_RE = re.compile(r'addToPageContent\(".*?\);', re.S)
_INSTITUTE_ARGS_RE = re.compile(r'^addToPageContent\("(.+)",\s*"(.+)"\);$', re.S)
_COURSE_RE = re.compile(r'<span class="text-form__item-name">\s*(\d+)\s*курс\s*</span>', re.S)
_GROUP_LINK_RE = re.compile(r'<a\s+href="/timetable/(\d+)"[^>]*>\s*([^<]+?)\s*</a>', re.S)

# Group page (`/timetable/{id}`): a weekday header's text can be immediately followed by a nested
# span with an illustrative date ("Вторник<span ...>1 сентября</span>") — capture up to the first
# nested tag, not up to a literal "</span>", since the date span means that closing tag isn't next.
_WEEKDAY_HEADER_RE = re.compile(r'<span class="info-block__header-text">\s*([^<]+)', re.S)
_LESSON_BLOCK_START_RE = re.compile(r'<div class="timetable__list-timeslot">', re.S)
_PERIOD_TIME_RE = re.compile(r"(\d+)\s*пара,\s*(\d{2}:\d{2})\s*[—-]\s*(\d{2}:\d{2})", re.S)
_KIND_DISCIPLINE_RE = re.compile(
    r'<span class="timetable__grid-text_gray">\s*([^<]+?)\s*</span>\s*([^<]+?)\s*<', re.S
)
_TITLE_ATTR_RE = re.compile(r'title="([^"]*)"')
_HREF_PEOPLE_RE = re.compile(r'href="/people/(\d+)/timetable"')
_SVG_STRIP_RE = re.compile(r"<svg.*?</svg>", re.S)
# The page renders every week's timetable twice: a mobile list (parsed here) immediately followed
# by a desktop-only grid duplicating the same lessons. This marker bounds each week's mobile
# section so the desktop duplicate never gets parsed as extra (or corrupted, run-on) lesson rows.
_DESKTOP_DUPLICATE_MARKER = '<div class="d-none d-md-block">'
# "Расписание действует с 01.09.2026 по 04.01.2027" — the term's date range, printed once near
# the top of every group page. This is the only anchor that lets a calendar date be mapped to
# week_parity 1/2 (verified against real data: the term's first week, starting 01.09.2026, a
# Tuesday, was the "I неделя" tab; the following Mon-Fri, 07-11.09.2026, was "II неделя").
_SEMESTER_RANGE_RE = re.compile(
    r"с\s*(\d{2})\.(\d{2})\.(\d{4})\s*по\s*(\d{2})\.(\d{2})\.(\d{4})", re.S
)

# Some groups (seen so far on what look like extramural/individual-schedule programs, labelled
# "Разовое" on the page's own single nav-tab) have NO id="week-1" markup at all -- their schedule
# is instead an explicit, per-calendar-date list embedded as this JSON assignment. See
# docs/tasks/043-rut-schedule-capability.md, "Addendum, 2026-09-02".
_TIMETABLE_DATA_MARKER = "window._timetableData = "


class MiitTimetableProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def provider_error_code(error: BaseException) -> str:
    if isinstance(error, MiitTimetableProviderError):
        return error.code
    if isinstance(error, httpx.TimeoutException):
        return "provider_timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return "provider_http_error"
    if isinstance(error, httpx.HTTPError):
        return "provider_network_unavailable"
    return "provider_unavailable"


def _icon_items(fragment: str, icon_class: str) -> list[dict[str, str | None]]:
    tag_re = re.compile(r"<(a|span)\b[^>]*\b" + re.escape(icon_class) + r"\b[^>]*>(.*?)</\1>", re.S)
    items: list[dict[str, str | None]] = []
    for match in tag_re.finditer(fragment):
        whole = match.group(0)
        opening_tag = whole[: whole.find(">") + 1]
        text = _SVG_STRIP_RE.sub("", match.group(2)).strip()
        title_match = _TITLE_ATTR_RE.search(opening_tag)
        href_match = _HREF_PEOPLE_RE.search(opening_tag)
        items.append(
            {
                "text": text,
                "title": title_match.group(1) if title_match else None,
                "person_id": href_match.group(1) if href_match else None,
            }
        )
    return items


def _joined(items: list[dict[str, str | None]], *, prefer_title: bool) -> str | None:
    values = [
        (item["title"] or item["text"]) if prefer_title else item["text"] for item in items if item["text"]
    ]
    return "; ".join(values) if values else None


_SUB_LESSON_SPLIT_RE = re.compile(r"<hr\s*/?>", re.S)


def _parse_sub_lesson(
    sub_html: str, *, weekday: int, week_parity: int, period_label: str, start_time: str, end_time: str
) -> ProviderLesson:
    kind_match = _KIND_DISCIPLINE_RE.search(sub_html)
    return ProviderLesson(
        weekday=weekday,
        week_parity=week_parity,
        period_label=period_label,
        start_time=start_time,
        end_time=end_time,
        lesson_kind=kind_match.group(1).strip() if kind_match else "",
        discipline=kind_match.group(2).strip() if kind_match else "",
        room=_joined(_icon_items(sub_html, "icon-location"), prefer_title=True),
        teachers=_joined(_icon_items(sub_html, "icon-academic-cap"), prefer_title=True),
        combined_groups=_joined(_icon_items(sub_html, "icon-community"), prefer_title=False),
    )


def _parse_week_fragment(fragment: str, week_parity: int) -> list[ProviderLesson]:
    events: list[tuple[int, str, int | tuple[int, int]]] = []
    for match in _WEEKDAY_HEADER_RE.finditer(fragment):
        name = match.group(1).strip().lower()
        weekday = _WEEKDAYS.get(name)
        if weekday is not None:
            events.append((match.start(), "weekday", weekday))
    starts = [match.start() for match in _LESSON_BLOCK_START_RE.finditer(fragment)]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(fragment)
        events.append((start, "lesson", (start, end)))
    events.sort(key=lambda event: event[0])

    lessons: list[ProviderLesson] = []
    current_weekday: int | None = None
    for _, kind, data in events:
        if kind == "weekday":
            current_weekday = data  # type: ignore[assignment]
            continue
        if current_weekday is None:
            continue
        start, end = data  # type: ignore[misc]
        slice_html = fragment[start:end]
        period_match = _PERIOD_TIME_RE.search(slice_html)
        if not period_match:
            continue
        period_label = f"{period_match.group(1)} пара"
        start_time, end_time = period_match.group(2), period_match.group(3)
        # A single time slot can hold more than one lesson -- typically the group split into
        # subgroups, each with its own discipline/teacher/room, separated on the page by "<hr>"
        # (verified against a real group page: 6 пара on a Thursday held two "Английский язык"
        # entries, one per "п/гр.", with different teachers and rooms). Each "<hr>"-separated
        # fragment becomes its own ProviderLesson sharing the same period/time/weekday.
        for sub_html in _SUB_LESSON_SPLIT_RE.split(slice_html[period_match.end() :]):
            if not sub_html.strip():
                continue
            lessons.append(
                _parse_sub_lesson(
                    sub_html,
                    weekday=current_weekday,
                    week_parity=week_parity,
                    period_label=period_label,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
    return lessons


def parse_hierarchy_html(html: str) -> ProviderHierarchy:
    institute_matches = list(_INSTITUTE_CALL_RE.finditer(html))
    bounds = [match.end() for match in institute_matches] + [len(html)]
    institutes: list[ProviderInstitute] = []
    groups: list[ProviderGroup] = []
    for index, match in enumerate(institute_matches):
        args_match = _INSTITUTE_ARGS_RE.match(match.group(0))
        if not args_match:
            continue
        external_id, name = args_match.group(1), args_match.group(2)
        institutes.append(ProviderInstitute(external_id=external_id, name=name))
        institute_chunk = html[match.end() : bounds[index + 1]]
        course_matches = list(_COURSE_RE.finditer(institute_chunk))
        course_bounds = [course.end() for course in course_matches] + [len(institute_chunk)]
        for course_index, course_match in enumerate(course_matches):
            course_number = int(course_match.group(1))
            course_chunk = institute_chunk[course_match.end() : course_bounds[course_index + 1]]
            for group_match in _GROUP_LINK_RE.finditer(course_chunk):
                groups.append(
                    ProviderGroup(
                        external_id=group_match.group(1),
                        name=group_match.group(2).strip(),
                        institute_external_id=external_id,
                        course_number=course_number,
                    )
                )
    return ProviderHierarchy(institutes=tuple(institutes), groups=tuple(groups))


def _parse_semester_range(html: str) -> tuple[date | None, date | None]:
    match = _SEMESTER_RANGE_RE.search(html)
    if not match:
        return None, None
    d1, m1, y1, d2, m2, y2 = match.groups()
    try:
        return date(int(y1), int(m1), int(d1)), date(int(y2), int(m2), int(d2))
    except ValueError:
        return None, None


def _extract_timetable_data(html: str) -> list | None:
    """Pulls the `window._timetableData = [...]` JSON array a "Разовое" (type=2) group page embeds
    instead of `id="week-1"` markup. Anchors a real JSON decoder at the marker (not a bracket-
    matching regex) since the array nests further arrays/objects (`timeSlots`, `events`, `rooms`,
    `groups`, `lecturers`) that would make a naive `\\[.*?\\]` match stop at the first nested `]`,
    long before the real end of the top-level array."""
    idx = html.find(_TIMETABLE_DATA_MARKER)
    if idx == -1:
        return None
    start = idx + len(_TIMETABLE_DATA_MARKER)
    try:
        data, _ = json.JSONDecoder().raw_decode(html, start)
    except ValueError:
        return None
    return data if isinstance(data, list) else None


def _joined_field(items: list, *, name_key: str, prefer_key: str | None = None) -> str | None:
    values: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = (item.get(prefer_key) if prefer_key else None) or item.get(name_key)
        if value:
            values.append(str(value))
    return "; ".join(values) if values else None


def _parse_dated_event(
    event: dict,
    *,
    weekday: int,
    lesson_date: date,
    start_time: str,
    end_time: str,
    group_external_id: str,
) -> ProviderLesson:
    # `groups` on a dated event includes the page's own group alongside any others the session is
    # shared with (unlike the type=1 HTML's `icon-community` tag, which only ever lists the
    # *other* groups) -- filter the current group out so `combined_groups` keeps the same "shared
    # with these other groups" meaning either way.
    other_groups = [
        g
        for g in (event.get("groups") or [])
        if isinstance(g, dict) and str(g.get("id")) != str(group_external_id)
    ]
    return ProviderLesson(
        weekday=weekday,
        # No "II неделя" tab exists for a "Разовое" page at all -- this value is never read by any
        # consumer once lesson_date is set (see ProviderLesson.lesson_date), so it's an inert
        # placeholder, not a real parity.
        week_parity=1,
        # These sessions have no "N пара" period grid (`slotName` is always null in every page
        # sampled so far) -- leave it blank rather than inventing a fake period number.
        period_label="",
        start_time=start_time,
        end_time=end_time,
        lesson_kind=(event.get("textTitle") or "").strip(),
        discipline=(event.get("text") or "").strip(),
        room=_joined_field(event.get("rooms") or [], name_key="name", prefer_key="hint"),
        teachers=_joined_field(event.get("lecturers") or [], name_key="shortFio", prefer_key="fullFio"),
        combined_groups=_joined_field(other_groups, name_key="name"),
        lesson_date=lesson_date,
    )


def _parse_timetable_data(data: list, group_external_id: str) -> list[ProviderLesson]:
    lessons: list[ProviderLesson] = []
    for day in data:
        if not isinstance(day, dict):
            continue
        hisdate = day.get("hisdate")
        if not hisdate:
            continue
        try:
            lesson_date = date.fromisoformat(hisdate)
        except ValueError:
            continue
        weekday = lesson_date.isoweekday()
        for slot in day.get("timeSlots") or []:
            if not isinstance(slot, dict):
                continue
            start_time = slot.get("slotStartDisplay") or ""
            end_time = slot.get("slotEndDisplay") or ""
            for event in slot.get("events") or []:
                if not isinstance(event, dict):
                    continue
                lessons.append(
                    _parse_dated_event(
                        event,
                        weekday=weekday,
                        lesson_date=lesson_date,
                        start_time=start_time,
                        end_time=end_time,
                        group_external_id=group_external_id,
                    )
                )
    return lessons


def parse_group_schedule_html(html: str, group_external_id: str) -> ProviderGroupLessons:
    semester_start, semester_end = _parse_semester_range(html)

    week1_start = html.find('id="week-1"')
    if week1_start == -1:
        timetable_data = _extract_timetable_data(html)
        if timetable_data is not None:
            lessons = _parse_timetable_data(timetable_data, group_external_id)
            return ProviderGroupLessons(
                lessons=tuple(lessons), semester_start=semester_start, semester_end=semester_end
            )
        return ProviderGroupLessons(lessons=(), semester_start=semester_start, semester_end=semester_end)
    week2_start = html.find('id="week-2"')

    week1_end = html.find(_DESKTOP_DUPLICATE_MARKER, week1_start)
    if week1_end == -1 or (week2_start != -1 and week1_end > week2_start):
        week1_end = week2_start if week2_start != -1 else len(html)
    lessons = _parse_week_fragment(html[week1_start:week1_end], 1)

    if week2_start != -1:
        week2_end = html.find(_DESKTOP_DUPLICATE_MARKER, week2_start)
        if week2_end == -1:
            week2_end = len(html)
        lessons += _parse_week_fragment(html[week2_start:week2_end], 2)
    return ProviderGroupLessons(
        lessons=tuple(lessons), semester_start=semester_start, semester_end=semester_end
    )


class MiitTimetableProvider:
    """Scrapes the university's own public timetable site (see docs/tasks/043-rut-schedule-
    capability.md, "Architecture" section) — a temporary provider until Oracle DB access exists,
    behind the same protocol shape `admission_rating`'s provider already establishes so an
    Oracle-backed provider can later join or replace it without touching any consumer."""

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(connect=5, read=20, write=5, pool=5),
            follow_redirects=False,
            verify=True,
            headers={"User-Agent": _USER_AGENT},
        )

    async def _get_html(self, client: httpx.AsyncClient, path: str) -> str:
        last_error: Exception | None = None
        for delay in _RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.get(path)
                response.raise_for_status()
                if len(response.content) > _MAX_RESPONSE_BYTES:
                    raise MiitTimetableProviderError("provider_response_too_large")
                return response.text
            except (httpx.HTTPError, MiitTimetableProviderError) as exc:
                last_error = exc
        if isinstance(last_error, MiitTimetableProviderError):
            raise last_error
        if isinstance(last_error, httpx.TimeoutException):
            raise MiitTimetableProviderError("provider_timeout") from last_error
        if isinstance(last_error, httpx.HTTPStatusError):
            raise MiitTimetableProviderError("provider_http_error") from last_error
        raise MiitTimetableProviderError("provider_network_unavailable") from last_error

    async def probe(self) -> None:
        async with self._client() as client:
            await self._get_html(client, "/timetable")

    async def read_hierarchy(self) -> ProviderHierarchy:
        async with self._client() as client:
            html = await self._get_html(client, "/timetable")
        try:
            hierarchy = parse_hierarchy_html(html)
        except (TypeError, ValueError) as exc:
            raise MiitTimetableProviderError("provider_response_invalid") from exc
        if not hierarchy.institutes or not hierarchy.groups:
            raise MiitTimetableProviderError("provider_response_invalid")
        return hierarchy

    async def read_group_lessons(self, group_external_id: str) -> ProviderGroupLessons:
        async with self._client() as client:
            html = await self._get_html(client, f"/timetable/{group_external_id}")
        try:
            return parse_group_schedule_html(html, group_external_id)
        except (TypeError, ValueError) as exc:
            raise MiitTimetableProviderError("provider_response_invalid") from exc
