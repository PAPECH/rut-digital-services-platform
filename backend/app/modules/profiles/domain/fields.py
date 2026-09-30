from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

PROFILE_FIELD_TYPES = {"string", "email", "phone", "boolean", "date", "number", "select"}
CORE_PROFILE_KEYS = frozenset(
    {"last_name", "first_name", "patronymic", "phone", "phone_verified", "email", "birth_date"}
)
DIRECT_OPTIONAL_PROFILE_KEYS = frozenset({"study_group", "job_title", "structural_unit"})

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class InvalidProfileField(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProfileFieldDefinition:
    key: str
    label: str
    type: str = "string"
    required: bool = False
    options: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ProfileFieldDefinition:
        key = str(value.get("key") or "").strip()
        label = str(value.get("label") or key).strip()
        field_type = str(value.get("type") or "string")
        options = tuple(str(option).strip() for option in value.get("options") or () if str(option).strip())
        if not key or key in CORE_PROFILE_KEYS:
            raise InvalidProfileField("Core profile fields cannot be configured per bot")
        if not label:
            raise InvalidProfileField("Profile field label is required")
        if field_type not in PROFILE_FIELD_TYPES:
            raise InvalidProfileField("Unsupported profile field type")
        if field_type == "select" and not options:
            raise InvalidProfileField("Select profile field requires options")
        return cls(
            key=key,
            label=label,
            type=field_type,
            required=bool(value.get("required")),
            options=options,
        )

    def normalize(self, value: Any) -> Any:
        if value is None or value == "":
            return None
        if self.type == "boolean":
            if not isinstance(value, bool):
                raise InvalidProfileField(f"{self.label}: expected boolean")
            return value
        if self.type == "number":
            if isinstance(value, bool):
                raise InvalidProfileField(f"{self.label}: expected number")
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError) as exc:
                raise InvalidProfileField(f"{self.label}: expected number") from exc
            return int(number) if number == number.to_integral_value() else float(number)

        text = str(value).strip()
        if len(text) > 2000:
            raise InvalidProfileField(f"{self.label}: value is too long")
        if self.type == "email" and not _EMAIL_RE.fullmatch(text):
            raise InvalidProfileField(f"{self.label}: invalid email")
        if self.type == "date":
            try:
                date.fromisoformat(text)
            except ValueError as exc:
                raise InvalidProfileField(f"{self.label}: invalid date") from exc
        if self.type == "select" and text not in self.options:
            raise InvalidProfileField(f"{self.label}: unknown option")
        return text or None
