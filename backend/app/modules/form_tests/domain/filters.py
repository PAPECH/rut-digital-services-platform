from __future__ import annotations

from typing import Any

from .errors import TestSchemaValidationError

MAX_FILTER_RULES = 20
_RULE_KEYS = {"min", "max", "label", "is_flagged", "recommendation_text"}


def _error(message: str, path: str) -> TestSchemaValidationError:
    return TestSchemaValidationError(message, path=path)


def validate_filters(  # noqa: PLR0912
    raw_filters: Any, known_result_scale_keys: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(raw_filters, list):
        raise _error("filters must be a list", "filters")

    normalized: list[dict[str, Any]] = []
    seen_scales: set[str] = set()
    for index, raw in enumerate(raw_filters):
        path = f"filters[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"result_scale_key", "rules"}:
            raise _error("Filter must contain exactly result_scale_key and rules", path)
        result_scale_key = raw["result_scale_key"]
        if result_scale_key not in known_result_scale_keys:
            raise _error("Filter references an unknown result scale", f"{path}.result_scale_key")
        if result_scale_key in seen_scales:
            raise _error("Only one filter per result scale is allowed", f"{path}.result_scale_key")
        seen_scales.add(result_scale_key)

        rules_raw = raw["rules"]
        if not isinstance(rules_raw, list) or not 1 <= len(rules_raw) <= MAX_FILTER_RULES:
            raise _error(f"rules must contain between 1 and {MAX_FILTER_RULES} items", f"{path}.rules")

        normalized_rules: list[dict[str, Any]] = []
        for rule_index, rule in enumerate(rules_raw):
            rule_path = f"{path}.rules[{rule_index}]"
            if not isinstance(rule, dict) or set(rule) - _RULE_KEYS:
                raise _error("Unknown rule properties", rule_path)
            minimum = rule.get("min")
            maximum = rule.get("max")
            for bound_name, bound in (("min", minimum), ("max", maximum)):
                if bound is not None and (isinstance(bound, bool) or not isinstance(bound, int | float)):
                    raise _error(f"{bound_name} must be a number or null", f"{rule_path}.{bound_name}")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise _error("min cannot be greater than max", rule_path)
            label = rule.get("label")
            if not isinstance(label, str) or not label.strip():
                raise _error("label is required", f"{rule_path}.label")
            is_flagged = rule.get("is_flagged", False)
            if not isinstance(is_flagged, bool):
                raise _error("is_flagged must be a boolean", f"{rule_path}.is_flagged")
            recommendation_text = rule.get("recommendation_text")
            if recommendation_text is not None and not isinstance(recommendation_text, str):
                raise _error(
                    "recommendation_text must be a string or null", f"{rule_path}.recommendation_text"
                )
            normalized_rules.append(
                {
                    "min": minimum,
                    "max": maximum,
                    "label": label,
                    "is_flagged": is_flagged,
                    "recommendation_text": recommendation_text,
                }
            )
        normalized.append({"result_scale_key": result_scale_key, "rules": normalized_rules})
    return normalized


def match_filter(rules: list[dict[str, Any]], value: float) -> dict[str, Any] | None:
    for rule in rules:
        lower_ok = rule["min"] is None or value >= rule["min"]
        upper_ok = rule["max"] is None or value <= rule["max"]
        if lower_ok and upper_ok:
            return rule
    return None


def match_all_filters(
    filters: list[dict[str, Any]],
    computed_values: dict[str, float],
) -> dict[str, dict[str, Any] | None]:
    matches: dict[str, dict[str, Any] | None] = {}
    for filt in filters:
        key = filt["result_scale_key"]
        value = computed_values.get(key)
        if value is None:
            continue
        matches[key] = match_filter(filt["rules"], value)
    return matches
