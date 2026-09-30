from __future__ import annotations

import pytest

from app.modules.form_tests.domain.elements import (
    validate_complete_answers,
    validate_elements,
    validate_partial_answers,
)
from app.modules.form_tests.domain.errors import TestAnswerValidationError, TestSchemaValidationError


def _choice_option(value: str, label: str, score: float) -> dict:
    return {"value": value, "label": label, "score": score}


def test_structural_elements_are_display_only_and_not_answerable() -> None:
    elements = validate_elements(
        [
            {"key": "ank_title", "type": "questionnaire_title", "label": "Анкета"},
            {"key": "stai_state_hdr", "type": "section_title", "label": "Бланк 1"},
            {"key": "ams_prompt", "type": "instruction", "label": "Оцените утверждения"},
        ]
    )
    assert [element["type"] for element in elements] == [
        "questionnaire_title",
        "section_title",
        "instruction",
    ]
    assert validate_partial_answers(elements, {}) == {}


def test_structural_element_rejects_answer_only_fields() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_elements([{"key": "x", "type": "section_title", "label": "Раздел", "required": True}])


@pytest.mark.parametrize("element_type", ["single_choice", "multiple_choice", "scale"])
def test_choice_types_require_options(element_type: str) -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_elements([{"key": "q1", "type": element_type, "label": "Q1", "required": True}])


def test_text_type_rejects_options_and_scoring_key() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_elements(
            [
                {
                    "key": "age",
                    "type": "text",
                    "label": "Возраст",
                    "required": False,
                    "scoring_key": "age",
                }
            ]
        )


def test_option_score_baked_directly_no_shared_response_scale() -> None:
    # Mirrors RUT's real content: a reverse-coded item's options carry their already-flipped
    # score directly, even though the label text is identical to a non-reversed item elsewhere.
    elements = validate_elements(
        [
            {
                "key": "stai_s_01",
                "type": "scale",
                "label": "Я спокоен",
                "required": True,
                "scoring_key": "stai_s_01",
                "options": [
                    _choice_option("1", "Нет, это не так", 4),
                    _choice_option("2", "Пожалуй, так", 3),
                    _choice_option("3", "Верно", 2),
                    _choice_option("4", "Совершенно верно", 1),
                ],
            },
            {
                "key": "stai_s_03",
                "type": "scale",
                "label": "Я нахожусь в напряжении",
                "required": True,
                "scoring_key": "stai_s_03",
                "options": [
                    _choice_option("1", "Нет, это не так", 1),
                    _choice_option("2", "Пожалуй, так", 2),
                    _choice_option("3", "Верно", 3),
                    _choice_option("4", "Совершенно верно", 4),
                ],
            },
        ]
    )
    by_key = {element["key"]: element for element in elements}
    assert by_key["stai_s_01"]["options"][0]["score"] == 4  # reverse-coded, baked already
    assert by_key["stai_s_03"]["options"][0]["score"] == 1  # direct item, same label text


def test_duplicate_element_key_rejected() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_elements(
            [
                {"key": "dup", "type": "text", "label": "A", "required": False},
                {"key": "dup", "type": "text", "label": "B", "required": False},
            ]
        )


def test_duplicate_scoring_key_rejected() -> None:
    option = _choice_option("1", "Да", 1)
    with pytest.raises(TestSchemaValidationError):
        validate_elements(
            [
                {
                    "key": "q1",
                    "type": "single_choice",
                    "label": "Q1",
                    "required": True,
                    "scoring_key": "dup",
                    "options": [option],
                },
                {
                    "key": "q2",
                    "type": "single_choice",
                    "label": "Q2",
                    "required": True,
                    "scoring_key": "dup",
                    "options": [option],
                },
            ]
        )


_MULTI_ELEMENTS = validate_elements(
    [
        {"key": "name", "type": "text", "label": "ФИО", "required": True},
        {
            "key": "activities",
            "type": "multiple_choice",
            "label": "Внеучебная деятельность",
            "required": False,
            "scoring_key": None,
            "options": [
                _choice_option("volunteering", "Волонтерство", 0),
                _choice_option("sports", "Спортивные секции", 0),
            ],
        },
        {
            "key": "mood",
            "type": "single_choice",
            "label": "Настроение",
            "required": True,
            "scoring_key": "mood",
            "options": [_choice_option("good", "Хорошо", 1), _choice_option("bad", "Плохо", 0)],
        },
    ]
)


def test_partial_answers_allow_missing_required_question() -> None:
    normalized = validate_partial_answers(_MULTI_ELEMENTS, {"name": "Иванов"})
    assert normalized == {"name": "Иванов"}


def test_complete_answers_enforce_required_question() -> None:
    with pytest.raises(TestAnswerValidationError):
        validate_complete_answers(_MULTI_ELEMENTS, {"name": "Иванов"})


def test_complete_answers_accept_full_submission() -> None:
    normalized = validate_complete_answers(
        _MULTI_ELEMENTS, {"name": "Иванов", "mood": "good", "activities": ["sports"]}
    )
    assert normalized["mood"] == "good"
    assert normalized["activities"] == ["sports"]


def test_unknown_question_key_rejected() -> None:
    with pytest.raises(TestAnswerValidationError):
        validate_partial_answers(_MULTI_ELEMENTS, {"nope": "x"})


def test_multiple_choice_rejects_unknown_option_and_duplicates() -> None:
    with pytest.raises(TestAnswerValidationError):
        validate_partial_answers(_MULTI_ELEMENTS, {"activities": ["not-an-option"]})
    with pytest.raises(TestAnswerValidationError):
        validate_partial_answers(_MULTI_ELEMENTS, {"activities": ["sports", "sports"]})


def test_single_choice_rejects_unknown_option() -> None:
    with pytest.raises(TestAnswerValidationError):
        validate_partial_answers(_MULTI_ELEMENTS, {"mood": "ecstatic"})
