from __future__ import annotations

from typing import Any

from .elements import known_scoring_keys, validate_elements
from .errors import TestSchemaValidationError
from .filters import validate_filters
from .scoring import validate_result_scales
from .template import validate_template

_TOP_LEVEL_KEYS = {"elements", "result_scales", "filters", "result_template"}


def validate_test_schema(raw: Any) -> dict[str, Any]:
    """Single entry point validating a whole `TestDraft`/`TestVersion` `schema` document --
    mirrors `forms.domain.fields.validate_form_fields` as the one place that must accept a
    schema before it is stored as a draft or published as a version."""
    if not isinstance(raw, dict) or set(raw) != _TOP_LEVEL_KEYS:
        raise TestSchemaValidationError(
            "schema must contain exactly elements, result_scales, filters, and result_template",
            path="schema",
        )

    elements = validate_elements(raw["elements"])
    scoring_keys = known_scoring_keys(elements)
    result_scales = validate_result_scales(raw["result_scales"], scoring_keys)
    result_scale_keys = {scale["key"] for scale in result_scales}
    filters = validate_filters(raw["filters"], result_scale_keys)
    result_template = validate_template(raw["result_template"], result_scale_keys)

    return {
        "elements": elements,
        "result_scales": result_scales,
        "filters": filters,
        "result_template": result_template,
    }


def validate_test_schema_draft(raw: Any) -> dict[str, Any]:
    """Permissive counterpart to `validate_test_schema`, used only by draft-save (Task 069) --
    mirrors `forms`' split between `SaveFormDraft`'s per-field checks and `PublishForm`'s
    completeness rule. Accepts an empty `result_scales`/`filters` list and a blank
    `result_template` so a test can be saved mid-authoring, before every piece exists; whatever
    *is* present still goes through the exact same per-item validators `validate_test_schema`
    uses, so a malformed individual element/term/rule/placeholder is rejected at every save, not
    just at publish."""
    if not isinstance(raw, dict) or set(raw) != _TOP_LEVEL_KEYS:
        raise TestSchemaValidationError(
            "schema must contain exactly elements, result_scales, filters, and result_template",
            path="schema",
        )

    elements = validate_elements(raw["elements"])
    scoring_keys = known_scoring_keys(elements)
    result_scales = validate_result_scales(raw["result_scales"], scoring_keys, require_non_empty=False)
    result_scale_keys = {scale["key"] for scale in result_scales}
    filters = validate_filters(raw["filters"], result_scale_keys)
    result_template = validate_template(raw["result_template"], result_scale_keys, require_non_blank=False)

    return {
        "elements": elements,
        "result_scales": result_scales,
        "filters": filters,
        "result_template": result_template,
    }
