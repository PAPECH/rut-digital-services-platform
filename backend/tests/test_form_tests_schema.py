from __future__ import annotations

import pytest

from app.modules.form_tests.domain.attempt_scoring import score_attempt
from app.modules.form_tests.domain.errors import TestAnswerValidationError, TestSchemaValidationError
from app.modules.form_tests.domain.schema import validate_test_schema

_VALID_RAW_SCHEMA = {
    "elements": [
        {"key": "title", "type": "questionnaire_title", "label": "Мини-тест"},
        {"key": "name", "type": "text", "label": "Ваше имя", "required": True},
        {
            "key": "mood",
            "type": "single_choice",
            "label": "Как ваше настроение?",
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
            "label": "Индекс дистресса",
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
    "result_template": (
        "Ваш индекс дистресса: {{result:distress.value}} ({{result:distress.label}}). "
        "{{#flagged:distress}}{{result:distress.recommendation}}{{/flagged:distress}}"
    ),
}


def test_validate_test_schema_end_to_end() -> None:
    schema = validate_test_schema(_VALID_RAW_SCHEMA)
    assert {element["key"] for element in schema["elements"]} == {"title", "name", "mood"}
    assert schema["result_scales"][0]["key"] == "distress"
    assert schema["filters"][0]["result_scale_key"] == "distress"


def test_validate_test_schema_rejects_unknown_top_level_key() -> None:
    broken = {**_VALID_RAW_SCHEMA, "extra": True}
    with pytest.raises(TestSchemaValidationError):
        validate_test_schema(broken)


def test_score_attempt_happy_path_flagged() -> None:
    schema = validate_test_schema(_VALID_RAW_SCHEMA)
    result = score_attempt(schema, {"name": "Иван", "mood": "bad"})
    assert result.computed_values["distress"] == 10
    assert result.matched_filters["distress"]["is_flagged"] is True
    assert "Обратитесь к специалисту." in result.rendered_result_text
    assert "10" in result.rendered_result_text


def test_score_attempt_not_flagged_path() -> None:
    schema = validate_test_schema(_VALID_RAW_SCHEMA)
    result = score_attempt(schema, {"name": "Иван", "mood": "good"})
    assert result.computed_values["distress"] == 0
    assert result.matched_filters["distress"]["is_flagged"] is False
    assert "Обратитесь к специалисту." not in result.rendered_result_text


def test_score_attempt_rejects_missing_required_answer() -> None:
    schema = validate_test_schema(_VALID_RAW_SCHEMA)
    with pytest.raises(TestAnswerValidationError):
        score_attempt(schema, {"name": "Иван"})
