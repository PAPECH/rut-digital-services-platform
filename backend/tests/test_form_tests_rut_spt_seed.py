from __future__ import annotations

from typing import Any

import pytest

from app.modules.form_tests.domain.attempt_scoring import score_attempt
from app.modules.form_tests.infrastructure.rut_spt_seed import build_rut_spt_schema

_EXPECTED_ELEMENT_COUNTS = {
    # 32 -> 28 (Task 080): ANK_01-04 (фамилия/имя/отчество/возраст) removed -- sourced from the
    # shared profile instead (last_name/first_name/patronymic/birth_date), no longer test questions.
    "ANK": 28,
    "BDI": 22,
    "STAI": 44,
    "AMS": 31,
    "SCU": 25,
    "BAT": 25,
    "BPNS": 23,
    "SURPS": 24,
    "BPAQ": 26,
}


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    return build_rut_spt_schema()


def test_schema_parses_and_validates_with_expected_element_counts(schema: dict[str, Any]) -> None:
    assert len(schema["elements"]) == sum(_EXPECTED_ELEMENT_COUNTS.values())
    counts: dict[str, int] = {}
    for element in schema["elements"]:
        prefix = element["key"].split("_")[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    assert counts == _EXPECTED_ELEMENT_COUNTS


def test_schema_has_29_result_scales_and_8_confirmed_filters(schema: dict[str, Any]) -> None:
    assert len(schema["result_scales"]) == 29
    assert {f["result_scale_key"] for f in schema["filters"]} == {
        "bdi_total",
        "stai_state",
        "stai_trait",
        "bat_overall",
        "bat_exhaustion",
        "bat_distancing",
        "bat_cognitive",
        "bat_emotional",
    }


def _answer_everything(schema: dict[str, Any], *, pick: str) -> dict[str, Any]:
    """`pick="first"` selects each question's first option (rawest value on every source-table
    scale); `pick="last"` selects each question's last option."""
    answers: dict[str, Any] = {}
    for element in schema["elements"]:
        if element["type"] == "text":
            answers[element["key"]] = "тест"
        elif element["type"] in {"single_choice", "scale"}:
            option = element["options"][0] if pick == "first" else element["options"][-1]
            answers[element["key"]] = option["value"]
        elif element["type"] == "multiple_choice":
            option = element["options"][0] if pick == "first" else element["options"][-1]
            answers[element["key"]] = [option["value"]]
    return answers


def test_uniform_lowest_answers_land_in_the_low_bat_and_moderate_anxiety_bands(
    schema: dict[str, Any],
) -> None:
    result = score_attempt(schema, _answer_everything(schema, pick="first"))
    # Every STAI item's raw value 1 selects its own already-direction-corrected option score;
    # a uniform selection makes Sigma1_raw == Sigma2_raw for both forms, so state anxiety lands
    # on the formula's bare constant (35) regardless of which uniform value was picked.
    assert result.computed_values["bdi_total"] == 0
    assert result.computed_values["stai_state"] == 35
    assert result.computed_values["stai_trait"] == 41
    assert result.computed_values["bat_overall"] == 1.0
    assert result.matched_filters["bdi_total"]["is_flagged"] is False
    assert result.matched_filters["stai_state"]["is_flagged"] is False
    assert result.matched_filters["stai_trait"]["is_flagged"] is False
    assert len(result.rendered_result_text) < 4000  # MAX's per-message limit


def test_uniform_highest_answers_flag_trait_but_not_state_anxiety(schema: dict[str, Any]) -> None:
    """State anxiety has an equal 10/10 direct/reverse split, so any uniform answer keeps
    Sigma1==Sigma2 and the score pinned at the formula's constant (35, "moderate"). Trait
    anxiety's 13/7 split is not symmetric, so a uniform *highest* answer (raw=4 on every item)
    pushes it up to `6*4 + 35 = 59`, past the TZ's 45-point "high, needs attention" threshold --
    a concrete case where the two forms genuinely diverge under the same input."""
    result = score_attempt(schema, _answer_everything(schema, pick="last"))
    assert result.computed_values["stai_state"] == 35
    assert result.computed_values["stai_trait"] == 59
    assert result.matched_filters["stai_state"]["is_flagged"] is False
    assert result.matched_filters["stai_trait"]["is_flagged"] is True
    assert "требует внимания" in result.matched_filters["stai_trait"]["label"]
    assert "требует внимания" in result.rendered_result_text


def test_depression_high_band_is_flagged_with_recommendation(schema: dict[str, Any]) -> None:
    result = score_attempt(schema, _answer_everything(schema, pick="last"))
    # Every BDI option's highest-scored choice is 3; 20 items x 3 = 60, the scale's max.
    assert result.computed_values["bdi_total"] == 60
    assert result.matched_filters["bdi_total"]["is_flagged"] is True
    assert "психиатр" in result.matched_filters["bdi_total"]["recommendation_text"]
    assert "психиатр" in result.rendered_result_text
