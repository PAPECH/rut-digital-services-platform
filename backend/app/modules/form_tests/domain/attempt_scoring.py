from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .elements import validate_complete_answers
from .filters import match_all_filters
from .scoring import compute_question_scores, evaluate_result_scales
from .template import render_result_template


@dataclass(frozen=True, slots=True)
class ScoredAttempt:
    answers: dict[str, Any]
    computed_values: dict[str, float]
    matched_filters: dict[str, dict[str, Any] | None]
    rendered_result_text: str


def score_attempt(schema: dict[str, Any], answers: dict[str, Any]) -> ScoredAttempt:
    """Finalize an attempt server-side: validate every required answer is present, compute
    every `ResultScale`, match each against its `Filter`, and render the result message --
    the only place a score or result text is ever produced. The client never submits one."""
    normalized_answers = validate_complete_answers(schema["elements"], answers)
    question_scores = compute_question_scores(schema["elements"], normalized_answers)
    computed_values = evaluate_result_scales(schema["result_scales"], question_scores)
    matched_filters = match_all_filters(schema["filters"], computed_values)
    rendered_result_text = render_result_template(schema["result_template"], computed_values, matched_filters)
    return ScoredAttempt(
        answers=normalized_answers,
        computed_values=computed_values,
        matched_filters=matched_filters,
        rendered_result_text=rendered_result_text,
    )
