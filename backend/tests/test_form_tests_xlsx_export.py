from __future__ import annotations

from datetime import UTC, date, datetime

from openpyxl import load_workbook

from app.modules.form_tests.domain.entities import TestAttempt, TestAttemptStatus
from app.modules.form_tests.domain.schema import validate_test_schema, validate_test_schema_draft
from app.modules.form_tests.infrastructure.xlsx_export import build_attempts_workbook

_SCHEMA = validate_test_schema(
    {
        "elements": [
            {"key": "name", "type": "text", "label": "Имя", "required": True},
            {
                "key": "mood",
                "type": "single_choice",
                "label": "Настроение",
                "required": True,
                "scoring_key": "mood",
                "options": [
                    {"value": "good", "label": "Хорошо", "score": 0},
                    {"value": "bad", "label": "Плохо", "score": 10},
                ],
            },
        ],
        "result_scales": [
            {
                "key": "distress",
                "label": "Дистресс",
                "terms": [{"question_key": "mood", "weight": 1}],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        "filters": [
            {
                "result_scale_key": "distress",
                "rules": [
                    {"min": 0, "max": 0, "label": "низкий", "is_flagged": False, "recommendation_text": None},
                    {
                        "min": 1,
                        "max": 10,
                        "label": "высокий",
                        "is_flagged": True,
                        "recommendation_text": "Обратитесь к специалисту.",
                    },
                ],
            }
        ],
        "result_template": "{{result:distress.value}}",
    }
)


def _attempt(
    attempt_id: int,
    *,
    answers: dict,
    computed_results: dict,
    consent_accepted: bool = False,
    consent_accepted_at: datetime | None = None,
    identity_snapshot: dict | None = None,
) -> TestAttempt:
    return TestAttempt(
        id=attempt_id,
        bot_instance_id=1,
        test_definition_id=1,
        test_version_id=1,
        user_id=42,
        status=TestAttemptStatus.COMPLETED,
        answers=answers,
        computed_results=computed_results,
        rendered_result_text="10",
        started_at=datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 9, 18, 10, 5, tzinfo=UTC),
        consent_accepted=consent_accepted,
        consent_accepted_at=consent_accepted_at,
        identity_snapshot=identity_snapshot,
    )


# Task 080: 5 identity columns (sourced from the profile, not test answers) sit right after
# "ID пользователя", before the pre-existing timestamp/consent/question/scale columns -- every
# fixed-index assertion below shifts by 5 relative to pre-Task-080 versions of this file.
_HEADERS = [
    "ID попытки",
    "ID пользователя",
    "Фамилия",
    "Имя",
    "Отчество",
    "Дата рождения",
    "Email",
    "Начата",
    "Завершена",
    "Согласие получено",
    "Дата согласия",
    "1) Имя",
    "2) Настроение",
    "Дистресс — значение",
    "Дистресс — интерпретация",
]


def test_workbook_has_expected_headers_and_rows_in_text_mode() -> None:
    attempts = [
        _attempt(
            1,
            answers={"name": "Иван", "mood": "bad"},
            computed_results={
                "distress": {
                    "value": 10,
                    "aggregation": "sum",
                    "filter": {
                        "label": "высокий",
                        "is_flagged": True,
                        "recommendation_text": "Обратитесь к специалисту.",
                    },
                }
            },
            consent_accepted=True,
            consent_accepted_at=datetime(2026, 9, 18, 10, 5, tzinfo=UTC),
            identity_snapshot={
                "last_name": "Иванов",
                "first_name": "Иван",
                "patronymic": "Иванович",
                "birth_date": "2000-01-02",
                "email": "ivan@example.com",
            },
        )
    ]

    workbook = build_attempts_workbook(_SCHEMA, attempts)
    sheet = workbook.active

    headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert headers == _HEADERS  # question columns (all of them) come before scale columns

    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[0:2] == [1, 42]
    assert row[2:7] == ["Иванов", "Иван", "Иванович", date(2000, 1, 2), "ivan@example.com"]
    assert row[9] == "да"
    assert row[10] == datetime(2026, 9, 18, 10, 5)
    assert row[11] == "Иван"  # unscored question shows the raw text answer
    assert row[12] == "Плохо"  # value_mode="text" (default): scored question shows its answer label
    assert row[13] == 10
    assert row[14] == "высокий"


def test_workbook_identity_columns_fall_back_to_live_profile_when_no_snapshot() -> None:
    """An attempt completed before Task 080 shipped has no `identity_snapshot`; the caller
    (`presentation.admin_router._load_identity_fallback`) supplies a live-profile lookup instead,
    keyed by `user_id`, so the export never shows a blank identity for it."""
    attempts = [_attempt(1, answers={"name": "Иван", "mood": "bad"}, computed_results={})]
    fallback = {
        42: {
            "last_name": "Петров",
            "first_name": "Пётр",
            "patronymic": "Петрович",
            "birth_date": date(1999, 5, 4),
            "email": "petr@example.com",
        }
    }
    workbook = build_attempts_workbook(_SCHEMA, attempts, fallback_identities=fallback)
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[2:7] == ["Петров", "Пётр", "Петрович", date(1999, 5, 4), "petr@example.com"]


def test_workbook_identity_columns_blank_when_neither_snapshot_nor_fallback_available() -> None:
    attempts = [_attempt(1, answers={"name": "Иван", "mood": "bad"}, computed_results={})]
    workbook = build_attempts_workbook(_SCHEMA, attempts)
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[2:7] == [None, None, None, None, None]


def test_workbook_shows_numeric_score_in_score_mode() -> None:
    attempts = [_attempt(1, answers={"name": "Иван", "mood": "bad"}, computed_results={})]
    workbook = build_attempts_workbook(_SCHEMA, attempts, value_mode="score")
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[11] == "Иван"  # a text question has no score: always falls back to its text answer
    assert row[12] == 10  # mood="bad" scores 10 per the schema's options


def test_workbook_multiple_choice_score_is_sum_of_selected_options() -> None:
    schema = validate_test_schema(
        {
            "elements": [
                {
                    "key": "symptoms",
                    "type": "multiple_choice",
                    "label": "Симптомы",
                    "required": False,
                    "scoring_key": "symptoms",
                    "options": [
                        {"value": "a", "label": "А", "score": 3},
                        {"value": "b", "label": "Б", "score": 4},
                    ],
                }
            ],
            "result_scales": [
                {
                    "key": "total",
                    "label": "Итого",
                    "terms": [{"question_key": "symptoms", "weight": 1}],
                    "constant": 0,
                    "aggregation": "sum",
                }
            ],
            "filters": [],
            "result_template": "{{result:total.value}}",
        }
    )
    attempt = _attempt(1, answers={"symptoms": ["a", "b"]}, computed_results={})
    workbook = build_attempts_workbook(schema, [attempt], value_mode="score")
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[11] == 7  # sum of selected options' scores (3 + 4)


def test_workbook_unscored_choice_question_always_shows_text_even_in_score_mode() -> None:
    """A question with no `scoring_key` must fall back to its text answer in score mode, even
    though its options still carry a `score` field (unused boilerplate on every anketa/demographic
    question per Task 068's schema shape) -- regression test for a bug caught against the live
    RUT SPT seed during Task 077 QA, where an unscored question's placeholder option score (0)
    was shown instead of its real text answer."""
    schema = validate_test_schema_draft(
        {
            "elements": [
                {
                    "key": "funding",
                    "type": "single_choice",
                    "label": "Вы обучаетесь на:",
                    "required": True,
                    "options": [
                        {"value": "opt1", "label": "Платном", "score": 5},
                        {"value": "opt2", "label": "Бюджете", "score": 5},
                    ],
                }
            ],
            "result_scales": [],
            "filters": [],
            "result_template": "",
        }
    )
    attempt = _attempt(1, answers={"funding": "opt2"}, computed_results={})
    workbook = build_attempts_workbook(schema, [attempt], value_mode="score")
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[11] == "Бюджете"  # not 5: no scoring_key means no formula ever consumes this option


def test_workbook_handles_missing_computed_value_gracefully() -> None:
    attempts = [_attempt(2, answers={"name": "Пётр"}, computed_results={})]
    workbook = build_attempts_workbook(_SCHEMA, attempts)
    sheet = workbook.active
    row = [cell.value for cell in next(sheet.iter_rows(min_row=2, max_row=2))]
    assert row[9] == "нет"
    assert row[10] is None
    assert row[12] == ""  # unanswered scored question: empty in text mode, not an error
    assert row[13] is None
    assert row[14] is None


def test_workbook_numbers_questions_sequentially_skipping_structural_elements_no_reset() -> None:
    """Question numbers count only answerable elements and never reset at a section/part
    boundary (confirmed product decision, Task 079) -- `section_title`/`instruction` are skipped
    entirely, not just unnumbered."""
    schema = validate_test_schema_draft(
        {
            "elements": [
                {"key": "title", "type": "questionnaire_title", "label": "Анкета"},
                {"key": "q1", "type": "text", "label": "Имя", "required": True},
                {"key": "instr", "type": "instruction", "label": "Оцените утверждения"},
                {"key": "q2", "type": "text", "label": "Фамилия", "required": True},
                {"key": "section", "type": "section_title", "label": "Часть 2"},
                {"key": "q3", "type": "text", "label": "Отчество", "required": True},
            ],
            "result_scales": [],
            "filters": [],
            "result_template": "",
        }
    )
    attempt = _attempt(1, answers={"q1": "А", "q2": "Б", "q3": "В"}, computed_results={})
    workbook = build_attempts_workbook(schema, [attempt])
    sheet = workbook.active
    headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert headers[11:14] == ["1) Имя", "2) Фамилия", "3) Отчество"]


def test_workbook_round_trips_through_openpyxl_load(tmp_path) -> None:
    attempts = [_attempt(3, answers={"name": "Анна", "mood": "good"}, computed_results={})]
    workbook = build_attempts_workbook(_SCHEMA, attempts)
    path = tmp_path / "export.xlsx"
    workbook.save(path)

    reloaded = load_workbook(path)
    sheet = reloaded.active
    assert sheet["A1"].value == "ID попытки"
    assert sheet["A2"].value == 3
