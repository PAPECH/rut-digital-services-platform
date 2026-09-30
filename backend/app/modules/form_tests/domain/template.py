from __future__ import annotations

import re
from typing import Any

from .errors import TestSchemaValidationError

MAX_TEMPLATE_LENGTH = 50_000

_PLACEHOLDER_RE = re.compile(r"\{\{result:([A-Za-z0-9_-]+)\.(value|label|recommendation)\}\}")
_BLOCK_RE = re.compile(r"\{\{#flagged:([A-Za-z0-9_-]+)\}\}(.*?)\{\{/flagged:\1\}\}", re.DOTALL)


def validate_template(
    template: Any,
    known_result_scale_keys: set[str],
    *,
    require_non_blank: bool = True,
) -> str:
    if not isinstance(template, str):
        raise TestSchemaValidationError("result_template must be a string", path="result_template")
    if require_non_blank and not template.strip():
        raise TestSchemaValidationError("result_template is required", path="result_template")
    if len(template) > MAX_TEMPLATE_LENGTH:
        raise TestSchemaValidationError("result_template is too long", path="result_template")
    for match in _PLACEHOLDER_RE.finditer(template):
        key = match.group(1)
        if key not in known_result_scale_keys:
            raise TestSchemaValidationError(
                f"Template references an unknown result scale: {key!r}", path="result_template"
            )
    for match in _BLOCK_RE.finditer(template):
        key = match.group(1)
        if key not in known_result_scale_keys:
            raise TestSchemaValidationError(
                f"Template block references an unknown result scale: {key!r}", path="result_template"
            )
    return template


def _format_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def render_result_template(
    template: str,
    computed_values: dict[str, float],
    matched_filters: dict[str, dict[str, Any] | None],
) -> str:
    """Mail-merge the result template against computed scale values -- deliberately not a
    general templating language: only `{{result:<key>.value|label|recommendation}}`
    placeholders and one conditional block per scale (`{{#flagged:<key>}}...{{/flagged:<key>}}`,
    kept only when that scale's matched filter has `is_flagged`), so a non-technical editor can
    safely change the text later without touching code."""

    def _resolve_block(match: re.Match[str]) -> str:
        key, body = match.group(1), match.group(2)
        matched = matched_filters.get(key)
        return body if matched is not None and matched.get("is_flagged") else ""

    rendered = _BLOCK_RE.sub(_resolve_block, template)

    def _resolve_placeholder(match: re.Match[str]) -> str:
        key, field_name = match.group(1), match.group(2)
        if field_name == "value":
            value = computed_values.get(key)
            return "" if value is None else _format_value(value)
        matched = matched_filters.get(key)
        if matched is None:
            return ""
        if field_name == "label":
            return matched.get("label") or ""
        return matched.get("recommendation_text") or ""

    return _PLACEHOLDER_RE.sub(_resolve_placeholder, rendered)
