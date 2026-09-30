from __future__ import annotations

import pytest

from app.modules.form_tests.domain.errors import TestSchemaValidationError
from app.modules.form_tests.domain.filters import match_all_filters, match_filter, validate_filters
from app.modules.form_tests.domain.template import render_result_template, validate_template

_DEPRESSION_RULES = [
    {"min": 0, "max": 12, "label": "нормальное состояние", "is_flagged": False, "recommendation_text": None},
    {
        "min": 13,
        "max": 17,
        "label": "умеренное снижение",
        "is_flagged": False,
        "recommendation_text": None,
    },
    {
        "min": 18,
        "max": 26,
        "label": "выраженное снижение",
        "is_flagged": True,
        "recommendation_text": "Может быть полезна помощь психолога.",
    },
    {
        "min": 27,
        "max": 60,
        "label": "сильное снижение",
        "is_flagged": True,
        "recommendation_text": "Необходима помощь психолога.",
    },
]


def test_validate_filters_accepts_known_scale_and_rejects_unknown() -> None:
    normalized = validate_filters(
        [{"result_scale_key": "depression", "rules": _DEPRESSION_RULES}], {"depression"}
    )
    assert normalized[0]["rules"][2]["is_flagged"] is True

    with pytest.raises(TestSchemaValidationError):
        validate_filters([{"result_scale_key": "ghost", "rules": _DEPRESSION_RULES}], {"depression"})


def test_validate_filters_rejects_duplicate_scale_and_bad_bounds() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_filters(
            [
                {"result_scale_key": "depression", "rules": _DEPRESSION_RULES},
                {"result_scale_key": "depression", "rules": _DEPRESSION_RULES},
            ],
            {"depression"},
        )
    with pytest.raises(TestSchemaValidationError):
        validate_filters(
            [{"result_scale_key": "depression", "rules": [{"min": 10, "max": 5, "label": "x"}]}],
            {"depression"},
        )


@pytest.mark.parametrize(
    ("value", "expected_label"),
    [
        (0, "нормальное состояние"),
        (12, "нормальное состояние"),
        (13, "умеренное снижение"),
        (26, "выраженное снижение"),
        (27, "сильное снижение"),
        (60, "сильное снижение"),
    ],
)
def test_match_filter_boundaries(value: int, expected_label: str) -> None:
    matched = match_filter(_DEPRESSION_RULES, value)
    assert matched is not None
    assert matched["label"] == expected_label


def test_match_all_filters_skips_unscored_result() -> None:
    filters = validate_filters(
        [{"result_scale_key": "depression", "rules": _DEPRESSION_RULES}], {"depression"}
    )
    matches = match_all_filters(filters, {})
    assert matches == {}


def test_template_placeholders_and_conditional_block() -> None:
    template = validate_template(
        "Депрессия: {{result:depression.value}} — {{result:depression.label}}. "
        "{{#flagged:depression}}Рекомендация: {{result:depression.recommendation}}{{/flagged:depression}}",
        {"depression"},
    )
    rendered_flagged = render_result_template(
        template, {"depression": 30}, {"depression": _DEPRESSION_RULES[3]}
    )
    assert "Рекомендация: Необходима помощь психолога." in rendered_flagged
    assert "30" in rendered_flagged

    rendered_not_flagged = render_result_template(
        template, {"depression": 5}, {"depression": _DEPRESSION_RULES[0]}
    )
    assert "Рекомендация" not in rendered_not_flagged


def test_template_rejects_reference_to_unknown_scale() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_template("{{result:ghost.value}}", {"depression"})


def test_template_missing_or_blank_rejected() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_template("   ", {"depression"})
