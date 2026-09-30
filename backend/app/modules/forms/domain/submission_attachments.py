from __future__ import annotations

from typing import Any, Mapping


def submission_attachment_fields(
    form_snapshot: Mapping[str, Any],
    values: Mapping[str, Any],
) -> dict[int, str]:
    """Map attachment IDs to their immutable submitted field keys."""

    result: dict[int, str] = {}
    fields = form_snapshot.get("fields")
    if not isinstance(fields, list):
        return result
    for field in fields:
        if not isinstance(field, dict) or field.get("type") != "file":
            continue
        key = str(field.get("key") or "")
        raw_ids = values.get(key)
        if not isinstance(raw_ids, list):
            continue
        for raw_id in raw_ids:
            if isinstance(raw_id, int) and not isinstance(raw_id, bool) and raw_id > 0:
                result[raw_id] = key
    return result
