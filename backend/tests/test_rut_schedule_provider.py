from __future__ import annotations

import json
from datetime import date

from app.modules.capabilities.rut_schedule.infrastructure.provider import (
    parse_group_schedule_html,
    parse_hierarchy_html,
)

_TYPE1_HTML = """
<html><body>
<p>Расписание действует с 01.09.2026 по 04.01.2027</p>
<div id="week-1">
<span class="info-block__header-text">Понедельник<span class="d">1 сентября</span></span>
<div class="timetable__list-timeslot">
1 пара, 09:00 - 10:30
<span class="timetable__grid-text_gray">лекция</span>Математика
<a href="/people/1/timetable" class="icon-academic-cap" title="Иванов Иван Иванович">Иванов И.И.</a>
<span class="icon-location" title="Ауд. 101">101</span>
</div>
</div>
<div class="d-none d-md-block">desktop duplicate, ignored</div>
</body></html>
"""

_TYPE2_HTML_TEMPLATE = """
<html><body>
<p>Расписание действует с 01.09.2026 по 04.01.2027</p>
<script>
window._timetableData = {payload};
</script>
<p>trailing page content after the assignment, e.g. more scripts/markup</p>
</body></html>
"""


def _type2_html(day_payload: list) -> str:
    return _TYPE2_HTML_TEMPLATE.format(payload=json.dumps(day_payload, ensure_ascii=False))


def _sample_event(**overrides) -> dict:
    event = {
        "periodicity": "ONCE",
        "textTitle": "Лекция",
        "text": "Высокоскоростной транспорт",
        "rooms": [{"id": 1, "name": "Аудитория 8516", "hint": "ГУК-8, 8516"}],
        "lecturers": [{"id": 1, "shortFio": "Корнетова М.П.", "fullFio": "Корнетова Мария Павловна"}],
        "groups": [
            {"id": 216161, "name": "ПИН-171"},
            {"id": 216272, "name": "ПСП-171"},
        ],
    }
    event.update(overrides)
    return event


def _sample_day(**overrides) -> dict:
    day = {
        "hisdate": "2026-09-02",
        "dayDisplay": "Среда",
        "timeSlots": [
            {
                "slotName": None,
                "slotStartDisplay": "18:30",
                "slotEndDisplay": "19:50",
                "events": [_sample_event()],
            }
        ],
    }
    day.update(overrides)
    return day


def test_type1_html_still_parses_via_id_week_markup() -> None:
    """Regression check: adding the group_external_id parameter and the type=2 branch must not
    change behavior for the far more common, already-working type=1 (id="week-1") shape."""
    result = parse_group_schedule_html(_TYPE1_HTML, "215959")

    assert len(result.lessons) == 1
    lesson = result.lessons[0]
    assert lesson.weekday == 1
    assert lesson.week_parity == 1
    assert lesson.discipline == "Математика"
    assert lesson.lesson_kind == "лекция"
    assert lesson.teachers == "Иванов Иван Иванович"
    assert lesson.room == "Ауд. 101"
    assert lesson.lesson_date is None
    assert result.semester_start == date(2026, 9, 1)
    assert result.semester_end == date(2027, 1, 4)


def test_type2_json_page_parses_dated_session() -> None:
    """"Разовое" (type=2) group pages have no id="week-1" at all -- their schedule comes from
    window._timetableData instead. See docs/tasks/043-rut-schedule-capability.md, "Addendum,
    2026-09-02"."""
    html = _type2_html([_sample_day()])

    result = parse_group_schedule_html(html, "216161")

    assert len(result.lessons) == 1
    lesson = result.lessons[0]
    assert lesson.lesson_date == date(2026, 9, 2)
    assert lesson.weekday == 3  # Wednesday, derived from hisdate -- matches "Среда"
    assert lesson.start_time == "18:30"
    assert lesson.end_time == "19:50"
    assert lesson.period_label == ""  # no "N пара" grid on these pages
    assert lesson.lesson_kind == "Лекция"
    assert lesson.discipline == "Высокоскоростной транспорт"
    assert lesson.room == "ГУК-8, 8516"  # prefers "hint" over "name"
    assert lesson.teachers == "Корнетова Мария Павловна"  # prefers "fullFio" over "shortFio"
    assert result.semester_start == date(2026, 9, 1)


def test_type2_json_excludes_the_page_s_own_group_from_combined_groups() -> None:
    """The `groups` array on a dated event includes the page's own group (216161) alongside any
    others it's shared with -- unlike the type=1 HTML's icon-community tag, which only lists the
    *other* groups. Must filter the current group out to keep the same meaning."""
    html = _type2_html([_sample_day()])

    result = parse_group_schedule_html(html, "216161")

    assert result.lessons[0].combined_groups == "ПСП-171"


def test_type2_json_survives_nested_arrays_and_trailing_page_content() -> None:
    """Regression guard for the bug this format change was built to avoid: a naive `\\[.*?\\]`
    regex would stop at the first nested `]` (inside `rooms`/`lecturers`/`groups`), truncating the
    JSON long before its real end. `_extract_timetable_data` uses a real JSON decoder instead, so
    it must correctly parse the full array regardless of nested brackets or what follows the `;`
    on the page."""
    two_days = [_sample_day(hisdate="2026-09-02"), _sample_day(hisdate="2026-09-05", dayDisplay="Суббота")]
    html = _type2_html(two_days)

    result = parse_group_schedule_html(html, "216161")

    assert len(result.lessons) == 2
    assert {lesson.lesson_date for lesson in result.lessons} == {date(2026, 9, 2), date(2026, 9, 5)}
    assert result.lessons[1].weekday == 6  # Saturday


def test_type2_json_tolerates_malformed_nested_entries() -> None:
    """The source site's own data isn't a contract this codebase controls -- a malformed/unexpected
    nested entry (not a dict where one is expected) must be skipped, not raise an unhandled
    AttributeError that would escape read_group_lessons' (TypeError, ValueError) handler."""
    day = _sample_day(
        timeSlots=[
            "not-a-dict-slot",
            {
                "slotName": None,
                "slotStartDisplay": "18:30",
                "slotEndDisplay": "19:50",
                "events": ["not-a-dict-event", _sample_event(groups=["not-a-dict-group"])],
            },
        ]
    )
    html = _type2_html([day])

    result = parse_group_schedule_html(html, "216161")

    assert len(result.lessons) == 1
    assert result.lessons[0].combined_groups is None


def test_neither_shape_present_returns_empty_not_an_error() -> None:
    html = "<html><body>Расписание действует с 01.09.2026 по 04.01.2027</body></html>"

    result = parse_group_schedule_html(html, "999999")

    assert result.lessons == ()
    assert result.semester_start == date(2026, 9, 1)


def _institute_section(course_number: int, group_id: str, group_name: str) -> str:
    return f"""
<div class="info-block__content info-block__content_top-padding">
<ul class="link-list text-form">
<li class="text-form__item">
<span class="text-form__item-name">{course_number} курс</span>
<span class="text-form__item-description">
<div class="timetable-url d-inline-block">
<a href="/timetable/{group_id}" title="Пример специальности">
{group_name} </a>
</div>
</span>
</li>
</ul>
</div>
"""


# Reproduces the real /timetable page's exact malformed announcement for "ПИШ "Академия ВСМ""
# (captured live from miit.ru/timetable): the source site itself embeds unescaped quotes in both
# the "id" and display-name arguments, breaking a naive `[^"]+`-per-argument regex.
_VSM_MALFORMED_CALL = (
    'addToPageContent("ПИШ-"Академия-ВСМ"", '
    '"Передовая инженерная школа «Академия ВСМ» (ПИШ "Академия ВСМ")");'
)


def test_malformed_vsm_institute_is_parsed_and_does_not_leak_into_neighbor() -> None:
    """Regression for the "ПИШ "Академия ВСМ"" gap: before the fix, the malformed announcement
    failed to match at all, and because institute boundaries are derived from match positions, its
    entire course/group section silently fell into the *previous* institute's chunk instead of just
    being dropped. See docs/tasks/043-rut-schedule-capability.md, "Addendum, 2026-09-04"."""
    html = f"""
<html><body>
<script>if(typeof addToPageContent === "function")addToPageContent("ИЭФ", "Институт экономики и финансов (ИЭФ)");</script>
{_institute_section(1, "111111", "ИЭФ-101")}
<script>if(typeof addToPageContent === "function"){_VSM_MALFORMED_CALL}</script>
{_institute_section(1, "222222", "ПИШ-101")}
<script>if(typeof addToPageContent === "function")addToPageContent("ЮИ", "Юридический институт (ЮИ)");</script>
{_institute_section(1, "333333", "ЮИ-101")}
</body></html>
"""

    result = parse_hierarchy_html(html)

    assert [institute.external_id for institute in result.institutes] == [
        "ИЭФ",
        'ПИШ-"Академия-ВСМ"',
        "ЮИ",
    ]
    vsm = result.institutes[1]
    assert vsm.name == 'Передовая инженерная школа «Академия ВСМ» (ПИШ "Академия ВСМ")'

    groups_by_institute: dict[str, list[str]] = {}
    for group in result.groups:
        groups_by_institute.setdefault(group.institute_external_id, []).append(group.external_id)

    assert groups_by_institute["ИЭФ"] == ["111111"]
    assert groups_by_institute['ПИШ-"Академия-ВСМ"'] == ["222222"]
    assert groups_by_institute["ЮИ"] == ["333333"]
