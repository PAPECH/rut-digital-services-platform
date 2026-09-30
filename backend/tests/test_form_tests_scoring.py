from __future__ import annotations

import pytest

from app.modules.form_tests.domain.elements import validate_elements
from app.modules.form_tests.domain.errors import ResultScaleError, TestSchemaValidationError
from app.modules.form_tests.domain.scoring import (
    compute_question_scores,
    evaluate_result_scales,
    validate_result_scales,
)

# --- Beck depression: a plain sum, no reverse items, constant 0 -----------------------------


def _beck_item(key: str, scores: list[int]) -> dict:
    return {
        "key": key,
        "type": "single_choice",
        "label": key,
        "required": True,
        "scoring_key": key,
        "options": [{"value": str(i), "label": str(i), "score": float(i)} for i in scores],
    }


def test_beck_style_plain_sum() -> None:
    elements = validate_elements([_beck_item(f"bdi_{i:02d}", [0, 1, 2, 3]) for i in range(1, 22)])
    scoring_keys = {element["scoring_key"] for element in elements}
    scale = validate_result_scales(
        [
            {
                "key": "depression",
                "label": "Депрессивная симптоматика",
                "terms": [{"question_key": key, "weight": 1} for key in scoring_keys],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        scoring_keys,
    )
    answers = {f"bdi_{i:02d}": "2" for i in range(1, 22)}  # everyone picks option "2"
    question_scores = compute_question_scores(elements, answers)
    computed = evaluate_result_scales(scale, question_scores)
    assert computed["depression"] == 21 * 2  # 42, within the source spec's 0-60 range


# --- Spielberger-Khanin: the state-vs-trait constant asymmetry found while planning ---------

# Item -> official raw response (1-4) used to build both the "official" Sigma1-Sigma2+K formula
# and this module's baked-option-score + constant formula, so the test fails if either the
# baked scores or the constant are wrong -- not just internally self-consistent.

_STATE_SIGMA1_ITEMS = [3, 4, 6, 7, 9, 12, 13, 14, 17, 18]  # "direct" (Sigma1)
_STATE_SIGMA2_ITEMS = [1, 2, 5, 8, 10, 11, 15, 16, 19, 20]  # "reverse" (Sigma2)
_TRAIT_SIGMA1_ITEMS = [2, 3, 4, 5, 8, 9, 11, 12, 14, 15, 17, 18, 20]  # form-2-local numbering
_TRAIT_SIGMA2_ITEMS = [1, 6, 7, 10, 13, 16, 19]


def _stai_item(key: str, *, reverse: bool) -> dict:
    # 1=Нет это не так .. 4=Совершенно верно; a reverse item's options are pre-flipped
    # (score = 5 - raw), exactly as RUT's own supplied content bakes it in per option.
    options = []
    for raw in (1, 2, 3, 4):
        score = (5 - raw) if reverse else raw
        options.append({"value": str(raw), "label": str(raw), "score": float(score)})
    return {
        "key": key,
        "type": "scale",
        "label": key,
        "required": True,
        "scoring_key": key,
        "options": options,
    }


def _build_stai_form(sigma1_items: list[int], sigma2_items: list[int], prefix: str) -> list[dict]:
    elements = []
    for item in sigma1_items:
        elements.append(_stai_item(f"{prefix}_{item:02d}", reverse=False))
    for item in sigma2_items:
        elements.append(_stai_item(f"{prefix}_{item:02d}", reverse=True))
    return validate_elements(elements)


def _official_formula(
    answers: dict[str, str], sigma1_items: list[int], sigma2_items: list[int], prefix: str, constant: int
) -> float:
    sigma1 = sum(int(answers[f"{prefix}_{item:02d}"]) for item in sigma1_items)
    sigma2 = sum(int(answers[f"{prefix}_{item:02d}"]) for item in sigma2_items)
    return float(sigma1 - sigma2 + constant)


@pytest.mark.parametrize("uniform_raw_answer", [1, 2, 3, 4])
def test_state_anxiety_needs_minus_fifteen_correction_not_zero(uniform_raw_answer: int) -> None:
    """10 reverse items x a (5-raw) flip contribute a flat +50 if just summed, but the
    official formula is Sigma1 - Sigma2 + 35 -- a scale built assuming baked scores already
    sum correctly (constant=0) would silently overstate every student's state-anxiety score
    by exactly 15 points, which is enough to cross the TZ's 44/45 risk-band boundary."""
    elements = _build_stai_form(_STATE_SIGMA1_ITEMS, _STATE_SIGMA2_ITEMS, "stai_s")
    scoring_keys = {element["scoring_key"] for element in elements}
    answers = {key: str(uniform_raw_answer) for key in scoring_keys}
    question_scores = compute_question_scores(elements, answers)

    official_value = _official_formula(
        answers, _STATE_SIGMA1_ITEMS, _STATE_SIGMA2_ITEMS, "stai_s", constant=35
    )

    correct_scale = validate_result_scales(
        [
            {
                "key": "stai_state",
                "label": "Ситуативная тревожность",
                "terms": [{"question_key": key, "weight": 1} for key in scoring_keys],
                "constant": -15,
                "aggregation": "sum",
            }
        ],
        scoring_keys,
    )
    assert evaluate_result_scales(correct_scale, question_scores)["stai_state"] == official_value

    naive_scale = validate_result_scales(
        [
            {
                "key": "stai_state",
                "label": "Ситуативная тревожность",
                "terms": [{"question_key": key, "weight": 1} for key in scoring_keys],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        scoring_keys,
    )
    naive_value = evaluate_result_scales(naive_scale, question_scores)["stai_state"]
    assert naive_value == official_value + 15  # the exact bug this test guards against


@pytest.mark.parametrize("uniform_raw_answer", [1, 2, 3, 4])
def test_trait_anxiety_needs_zero_correction_not_minus_fifteen(uniform_raw_answer: int) -> None:
    """The trait form has only 7 reverse items (7x5=35), so its baked-score sum already equals
    Sigma1-Sigma2+35 with constant=0 -- confirms the correction is scale-specific (depends on
    each scale's own reverse-item count), not a universal -15 fudge factor."""
    elements = _build_stai_form(_TRAIT_SIGMA1_ITEMS, _TRAIT_SIGMA2_ITEMS, "stai_t")
    scoring_keys = {element["scoring_key"] for element in elements}
    answers = {key: str(uniform_raw_answer) for key in scoring_keys}
    question_scores = compute_question_scores(elements, answers)

    official_value = _official_formula(
        answers, _TRAIT_SIGMA1_ITEMS, _TRAIT_SIGMA2_ITEMS, "stai_t", constant=35
    )

    scale = validate_result_scales(
        [
            {
                "key": "stai_trait",
                "label": "Личностная тревожность",
                "terms": [{"question_key": key, "weight": 1} for key in scoring_keys],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        scoring_keys,
    )
    assert evaluate_result_scales(scale, question_scores)["stai_trait"] == official_value


# --- BAT-style average and scale-of-scales ---------------------------------------------------


def test_mean_aggregation_and_scale_of_scales() -> None:
    elements = validate_elements([_beck_item(f"bat_{i:02d}", [1, 2, 3, 4, 5]) for i in range(1, 9)])
    scoring_keys = [f"bat_{i:02d}" for i in range(1, 9)]
    exhaustion = {
        "key": "bat_exhaustion",
        "label": "Истощение",
        "terms": [{"question_key": key, "weight": 1} for key in scoring_keys],
        "constant": 0,
        "aggregation": "mean",
    }
    scales = validate_result_scales([exhaustion], set(scoring_keys))
    answers = {key: "3" for key in scoring_keys}
    question_scores = compute_question_scores(elements, answers)
    computed = evaluate_result_scales(scales, question_scores)
    assert computed["bat_exhaustion"] == 3.0  # average of eight 3s

    overall_scales = validate_result_scales(
        [
            exhaustion,
            {
                "key": "bat_overall",
                "label": "Общий балл",
                "terms": [{"result_scale_key": "bat_exhaustion", "weight": 1}],
                "constant": 0,
                "aggregation": "mean",
            },
        ],
        set(scoring_keys),
    )
    computed_overall = evaluate_result_scales(overall_scales, question_scores)
    assert computed_overall["bat_overall"] == 3.0
    assert computed_overall["bat_exhaustion"] == 3.0


def test_academic_motivation_style_fixed_four_item_subscale() -> None:
    elements = validate_elements([_beck_item(f"ams_{i:02d}", [1, 2, 3, 4, 5]) for i in range(1, 29)])
    cognitive_keys = ["ams_01", "ams_08", "ams_15", "ams_22"]  # per Приложение 1
    scale = validate_result_scales(
        [
            {
                "key": "ams_cognitive",
                "label": "Познавательная мотивация",
                "terms": [{"question_key": key, "weight": 1} for key in cognitive_keys],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        {f"ams_{i:02d}" for i in range(1, 29)},
    )
    answers = {f"ams_{i:02d}": "5" for i in range(1, 29)}
    question_scores = compute_question_scores(elements, answers)
    computed = evaluate_result_scales(scale, question_scores)
    assert computed["ams_cognitive"] == 20  # 4 items x 5 (max), matches the spec's "out of 20" range


# --- Structural correctness checks ------------------------------------------------------------


def test_cycle_detected_at_validation_time() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_result_scales(
            [
                {
                    "key": "a",
                    "label": "A",
                    "terms": [{"result_scale_key": "b", "weight": 1}],
                    "constant": 0,
                    "aggregation": "sum",
                },
                {
                    "key": "b",
                    "label": "B",
                    "terms": [{"result_scale_key": "a", "weight": 1}],
                    "constant": 0,
                    "aggregation": "sum",
                },
            ],
            set(),
        )


def test_term_referencing_unknown_scoring_key_rejected() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_result_scales(
            [
                {
                    "key": "a",
                    "label": "A",
                    "terms": [{"question_key": "ghost", "weight": 1}],
                    "constant": 0,
                    "aggregation": "sum",
                }
            ],
            set(),
        )


def test_weight_must_be_plus_or_minus_one() -> None:
    with pytest.raises(TestSchemaValidationError):
        validate_result_scales(
            [
                {
                    "key": "a",
                    "label": "A",
                    "terms": [{"question_key": "q", "weight": 2}],
                    "constant": 0,
                    "aggregation": "sum",
                }
            ],
            {"q"},
        )


def test_evaluate_raises_when_referenced_question_unanswered() -> None:
    scale = validate_result_scales(
        [
            {
                "key": "a",
                "label": "A",
                "terms": [{"question_key": "q", "weight": 1}],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        {"q"},
    )
    with pytest.raises(ResultScaleError):
        evaluate_result_scales(scale, {})
