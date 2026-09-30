"""`show_scores` redaction at the API boundary (Task 075) -- the one place `computed_results` is
hidden from a student's own read. Everything below it (domain, use cases, repositories) stays
truthful; see `test_form_tests_use_cases.py` for that layer's coverage."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.form_tests.domain.entities import TestAttempt, TestAttemptStatus
from app.modules.form_tests.presentation.router import _attempt_out

_COMPUTED_RESULTS = {"distress": {"value": 10, "aggregation": "sum", "filter": None}}


def _make_attempt(computed_results: dict | None) -> TestAttempt:
    now = datetime.now(tz=UTC)
    return TestAttempt(
        id=1,
        bot_instance_id=1,
        test_definition_id=1,
        test_version_id=1,
        user_id=1,
        status=TestAttemptStatus.COMPLETED if computed_results is not None else TestAttemptStatus.IN_PROGRESS,
        answers={"mood": "bad"},
        computed_results=computed_results,
        rendered_result_text="10" if computed_results is not None else None,
        started_at=now,
        completed_at=now if computed_results is not None else None,
    )


def test_attempt_out_hides_computed_results_when_show_scores_is_off() -> None:
    out = _attempt_out(_make_attempt(_COMPUTED_RESULTS), show_scores=False)
    assert out.computed_results is None
    assert out.rendered_result_text == "10"  # interpretation text is never redacted


def test_attempt_out_exposes_computed_results_when_show_scores_is_on() -> None:
    out = _attempt_out(_make_attempt(_COMPUTED_RESULTS), show_scores=True)
    assert out.computed_results == _COMPUTED_RESULTS


def test_attempt_out_show_scores_is_moot_when_nothing_is_computed_yet() -> None:
    attempt = _make_attempt(None)
    assert _attempt_out(attempt, show_scores=False).computed_results is None
    assert _attempt_out(attempt, show_scores=True).computed_results is None
