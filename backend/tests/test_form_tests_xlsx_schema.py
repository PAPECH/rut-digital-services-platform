from __future__ import annotations

from io import BytesIO

import pytest

from app.modules.form_tests.domain.schema import validate_test_schema
from app.modules.form_tests.infrastructure.xlsx_schema import (
    XlsxSchemaError,
    read_schema_workbook,
    write_schema_workbook,
)

_SCHEMA = validate_test_schema(
    {
        "elements": [
            {"key": "title", "type": "questionnaire_title", "label": "Заголовок"},
            {"key": "age", "type": "text", "label": "Ваш возраст", "required": True},
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
            {
                "key": "hobby",
                "type": "multiple_choice",
                "label": "Хобби (не влияет на баллы)",
                "required": False,
                "options": [
                    {"value": "a", "label": "Спорт", "score": 0},
                    {"value": "b", "label": "Музыка", "score": 0},
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
            },
            {
                "key": "overall",
                "label": "Итог",
                "terms": [{"result_scale_key": "distress", "weight": 1}],
                "constant": 5,
                "aggregation": "mean",
            },
        ],
        "filters": [
            {
                "result_scale_key": "distress",
                "rules": [
                    {"min": None, "max": 5, "label": "Низкий", "is_flagged": False, "recommendation_text": None},
                    {"min": 5, "max": None, "label": "Высокий", "is_flagged": True, "recommendation_text": "См. специалиста"},
                ],
            }
        ],
        "result_template": "{{result:distress.value}} — {{result:distress.label}}\n\nИтог: {{result:overall.value}}",
    }
)


def _round_trip(schema: dict) -> dict:
    workbook = write_schema_workbook(name="Мой тест", intro_text="Вводный текст", schema=schema)
    buffer = BytesIO()
    workbook.save(buffer)
    return read_schema_workbook(buffer.getvalue())


def test_round_trip_preserves_name_and_intro_text() -> None:
    result = _round_trip(_SCHEMA)
    assert result["name"] == "Мой тест"
    assert result["intro_text"] == "Вводный текст"


def test_round_trip_preserves_elements_including_required_and_scoring() -> None:
    result = _round_trip(_SCHEMA)
    elements = {e["key"]: e for e in result["test_schema"]["elements"]}
    assert elements["title"]["type"] == "questionnaire_title"
    assert elements["age"]["type"] == "text"
    assert elements["age"]["required"] is True
    assert elements["mood"]["scoring_key"] == "mood"
    assert [o["score"] for o in elements["mood"]["options"]] == [0.0, 10.0]
    # Unscored choice element: scores must not leak through as real numbers on re-import.
    assert elements["hobby"]["scoring_key"] is None
    assert elements["hobby"]["required"] is False
    assert [o["score"] for o in elements["hobby"]["options"]] == [0.0, 0.0]


def test_round_trip_preserves_result_scales_including_scale_of_scales() -> None:
    result = _round_trip(_SCHEMA)
    scales = {s["key"]: s for s in result["test_schema"]["result_scales"]}
    assert scales["distress"]["terms"] == [{"question_key": "mood", "result_scale_key": None, "weight": 1.0}]
    assert scales["overall"]["terms"] == [{"question_key": None, "result_scale_key": "distress", "weight": 1.0}]
    assert scales["overall"]["constant"] == 5.0
    assert scales["overall"]["aggregation"] == "mean"


def test_round_trip_preserves_filters_and_negative_weights() -> None:
    # A fresh raw schema, not `_SCHEMA` reused as input: `_SCHEMA` is itself
    # `validate_test_schema`'s *normalized* output (e.g. every text element already carries a
    # stray `scoring_key: None`, which `validate_elements` rejects as an unknown property on a
    # second pass) -- feeding normalized output back in as raw input is exactly the class of
    # double-validation mistake this module's own idempotency work is about avoiding elsewhere.
    schema_with_negative_weight = validate_test_schema(
        {
            "elements": [
                {
                    "key": "mood",
                    "type": "single_choice",
                    "label": "Настроение",
                    "scoring_key": "mood",
                    "options": [
                        {"value": "good", "label": "Хорошо", "score": 0},
                        {"value": "bad", "label": "Плохо", "score": 10},
                    ],
                }
            ],
            "result_scales": [
                {
                    "key": "distress",
                    "label": "Дистресс",
                    "terms": [{"question_key": "mood", "weight": 1}],
                    "constant": 0,
                    "aggregation": "sum",
                },
                {
                    "key": "overall",
                    "label": "Итог",
                    "terms": [{"result_scale_key": "distress", "weight": -1}],
                    "constant": 5,
                    "aggregation": "mean",
                },
            ],
            "filters": _SCHEMA["filters"],
            "result_template": "{{result:distress.value}}",
        }
    )
    result = _round_trip(schema_with_negative_weight)
    assert result["test_schema"]["result_scales"][1]["terms"][0]["weight"] == -1.0

    filters = result["test_schema"]["filters"]
    assert filters == _SCHEMA["filters"]


def test_round_trip_preserves_multiline_template() -> None:
    result = _round_trip(_SCHEMA)
    assert result["test_schema"]["result_template"] == _SCHEMA["result_template"]


def test_round_trip_preserves_leading_and_trailing_blank_lines_in_template_and_intro() -> None:
    """Regression test: `.strip()`-based cell reading used to silently drop a leading/trailing
    blank line from the template and intro text -- meaningful admin-authored spacing in what the
    student reads, not incidental whitespace."""
    schema = {**_SCHEMA, "result_template": "\nСпасибо за участие!\n\nВаш результат готов.\n\n"}
    workbook = write_schema_workbook(name="x", intro_text="\nЧитайте внимательно.\n\n", schema=schema)
    buffer = BytesIO()
    workbook.save(buffer)
    result = read_schema_workbook(buffer.getvalue())
    assert result["test_schema"]["result_template"] == schema["result_template"]
    assert result["intro_text"] == "\nЧитайте внимательно.\n\n"


def test_round_trip_result_revalidates_cleanly_through_the_strict_validator() -> None:
    """The whole point of matching the draft/version shape exactly: what comes back must be
    directly publishable, the same way a hand-typed draft is."""
    result = _round_trip(_SCHEMA)
    validate_test_schema(result["test_schema"])


def test_missing_sheet_raises_xlsx_schema_error() -> None:
    workbook = write_schema_workbook(name="x", intro_text=None, schema=_SCHEMA)
    del workbook["Фильтры"]
    buffer = BytesIO()
    workbook.save(buffer)
    with pytest.raises(XlsxSchemaError):
        read_schema_workbook(buffer.getvalue())


def test_corrupt_file_raises_xlsx_schema_error() -> None:
    with pytest.raises(XlsxSchemaError):
        read_schema_workbook(b"not an xlsx file at all")


def test_malformed_term_string_raises_xlsx_schema_error() -> None:
    workbook = write_schema_workbook(name="x", intro_text=None, schema=_SCHEMA)
    scales_sheet = workbook["Шкалы"]
    scales_sheet.append(["broken", "Сломанная шкала", "no-colon-here", 0, "sum"])
    buffer = BytesIO()
    workbook.save(buffer)
    with pytest.raises(XlsxSchemaError):
        read_schema_workbook(buffer.getvalue())
