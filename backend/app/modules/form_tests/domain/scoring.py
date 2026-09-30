from __future__ import annotations

import re
from typing import Any

from .errors import ResultScaleError, TestSchemaValidationError

AGGREGATIONS = {"sum", "mean"}
_VALID_WEIGHTS = (1, -1, 1.0, -1.0)
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def compute_question_scores(
    elements: list[dict[str, Any]],
    answers: dict[str, Any],
) -> dict[str, float]:
    """Map each scored question's `scoring_key` to the numeric score its answer contributes.

    `single_choice`/`scale` contribute their one selected option's score; `multiple_choice`
    contributes the sum of every selected option's score. An unanswered or unscored question
    contributes nothing -- callers decide whether a `ResultScale` term left unanswered is an
    error (see `evaluate_result_scales`).
    """
    scores: dict[str, float] = {}
    for element in elements:
        scoring_key = element.get("scoring_key")
        if not scoring_key:
            continue
        raw = answers.get(element["key"])
        if raw is None:
            continue
        option_scores = {option["value"]: option["score"] for option in element["options"]}
        if element["type"] in {"single_choice", "scale"}:
            scores[scoring_key] = option_scores[raw]
        elif element["type"] == "multiple_choice":
            scores[scoring_key] = sum(option_scores[value] for value in raw)
    return scores


def _topological_order(result_scales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {scale["key"]: scale for scale in result_scales}
    order: list[dict[str, Any]] = []
    state: dict[str, str] = {}  # key -> "visiting" | "done"

    def visit(key: str, path: list[str]) -> None:
        if state.get(key) == "done":
            return
        if state.get(key) == "visiting":
            cycle = " -> ".join([*path, key])
            raise ResultScaleError(f"Result scale dependency cycle: {cycle}", result_scale_key=key)
        scale = by_key.get(key)
        if scale is None:
            raise ResultScaleError(f"Unknown result scale referenced: {key}", result_scale_key=key)
        state[key] = "visiting"
        for term in scale["terms"]:
            dependency = term.get("result_scale_key")
            if dependency is not None:
                visit(dependency, [*path, key])
        state[key] = "done"
        order.append(scale)

    for scale in result_scales:
        visit(scale["key"], [])
    return order


def evaluate_result_scales(
    result_scales: list[dict[str, Any]],
    question_scores: dict[str, float],
) -> dict[str, float]:
    """Compute every `ResultScale`'s value, resolving scale-of-scales dependencies first.

    Each scale is `sum(weight * term_value for term in terms) + constant`, divided by
    `len(terms)` when `aggregation == "mean"`. A term is either a raw question's score
    (`question_key`, via `question_scores`) or another already-computed `ResultScale`'s value
    (`result_scale_key`) -- evaluated in dependency order so a scale-of-scales sees its
    dependencies' final values, never their raw inputs.
    """
    ordered = _topological_order(result_scales)
    computed: dict[str, float] = {}
    for scale in ordered:
        total = 0.0
        for term in scale["terms"]:
            weight = term["weight"]
            question_key = term.get("question_key")
            if question_key is not None:
                if question_key not in question_scores:
                    raise ResultScaleError(
                        f"Result scale {scale['key']!r} references unanswered question {question_key!r}",
                        result_scale_key=scale["key"],
                    )
                total += weight * question_scores[question_key]
            else:
                total += weight * computed[term["result_scale_key"]]
        total += scale["constant"]
        if scale["aggregation"] == "mean":
            total /= len(scale["terms"])
        computed[scale["key"]] = total
    return computed


def _error(message: str, path: str) -> TestSchemaValidationError:
    return TestSchemaValidationError(message, path=path)


def validate_result_scales(  # noqa: PLR0912, PLR0915
    raw_scales: Any,
    known_scoring_keys: set[str],
    *,
    require_non_empty: bool = True,
) -> list[dict[str, Any]]:
    if not isinstance(raw_scales, list):
        raise _error("result_scales must be a list", "result_scales")
    if require_non_empty and not raw_scales:
        raise _error("result_scales must be a non-empty list", "result_scales")

    normalized: list[dict[str, Any]] = []
    keys: set[str] = set()
    for index, raw in enumerate(raw_scales):
        path = f"result_scales[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"key", "label", "terms", "constant", "aggregation"}:
            raise _error(
                "Result scale must contain exactly key, label, terms, constant, and aggregation", path
            )
        key = raw["key"]
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise _error("Invalid result scale key", f"{path}.key")
        if key in keys:
            raise _error("Result scale keys must be unique", f"{path}.key")
        keys.add(key)

        label = raw["label"]
        if not isinstance(label, str) or not label.strip():
            raise _error("Result scale label is required", f"{path}.label")

        aggregation = raw["aggregation"]
        if aggregation not in AGGREGATIONS:
            raise _error("Unknown aggregation", f"{path}.aggregation")

        constant = raw["constant"]
        if isinstance(constant, bool) or not isinstance(constant, int | float):
            raise _error("constant must be a number", f"{path}.constant")

        terms_raw = raw["terms"]
        if not isinstance(terms_raw, list) or not terms_raw:
            raise _error("terms must be a non-empty list", f"{path}.terms")

        normalized_terms: list[dict[str, Any]] = []
        for term_index, term in enumerate(terms_raw):
            term_path = f"{path}.terms[{term_index}]"
            if not isinstance(term, dict):
                raise _error("Term must be an object", term_path)
            # Value presence, not key presence: makes this check idempotent on its own
            # normalized output (which always carries both keys, one `None`), so re-validating
            # an already-normalized schema -- as Task 069's draft-save-then-publish flow does --
            # doesn't misread a legitimate term as referencing both/neither.
            has_question = term.get("question_key") is not None
            has_scale = term.get("result_scale_key") is not None
            if has_question == has_scale:
                raise _error("Term must reference exactly one of question_key or result_scale_key", term_path)
            weight = term.get("weight")
            if weight not in _VALID_WEIGHTS:
                raise _error("weight must be +1 or -1", f"{term_path}.weight")
            if has_question:
                question_key = term["question_key"]
                if question_key not in known_scoring_keys:
                    raise _error("Term references an unknown scoring_key", f"{term_path}.question_key")
                normalized_terms.append(
                    {"question_key": question_key, "result_scale_key": None, "weight": float(weight)}
                )
            else:
                normalized_terms.append(
                    {
                        "question_key": None,
                        "result_scale_key": term["result_scale_key"],
                        "weight": float(weight),
                    }
                )

        normalized.append(
            {
                "key": key,
                "label": label,
                "terms": normalized_terms,
                "constant": float(constant),
                "aggregation": aggregation,
            }
        )

    for scale in normalized:
        for term in scale["terms"]:
            dependency = term["result_scale_key"]
            if dependency is not None and dependency not in keys:
                raise _error(
                    f"Term references an unknown result scale: {dependency!r}",
                    f"result_scales.{scale['key']}",
                )
    try:
        _topological_order(normalized)
    except ResultScaleError as exc:
        raise _error(str(exc), "result_scales") from exc

    return normalized
