from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .entities import SharedProfile
from .fields import ProfileFieldDefinition

CORE_REQUIREMENTS = (
    ("last_name", "Фамилия"),
    ("first_name", "Имя"),
    ("patronymic", "Отчество"),
)


def _empty(value: Any, *, requires_true: bool = False) -> bool:
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (requires_true and value is not True)
    )


def find_missing_required_fields(
    profile: SharedProfile,
    schema: Iterable[Mapping[str, Any]],
    local_data: Mapping[str, Any] | None = None,
) -> list[str]:
    missing = [label for key, label in CORE_REQUIREMENTS if _empty(getattr(profile, key, None))]
    if _empty(profile.phone) or not profile.phone_verified:
        missing.append("Подтверждённый телефон")

    tenant_values = local_data or {}
    for raw_field in schema:
        try:
            field = ProfileFieldDefinition.from_mapping(raw_field)
        except ValueError:
            continue
        if not field.required:
            continue
        value = getattr(profile, field.key, None)
        if value is None:
            value = tenant_values.get(field.key, profile.shared_data.get(field.key))
        if _empty(value, requires_true=field.type == "boolean"):
            missing.append(field.label)
    return missing
