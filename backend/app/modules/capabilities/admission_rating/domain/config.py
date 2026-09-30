from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

_MARKUP_RE = re.compile(r"<[^>]+>")
_ALLOWED_KEYS = {
    "provider",
    "admission_year",
    "polling_interval_seconds",
    "notifications_enabled",
    "title",
    "subtitle",
    "lookup_label",
    "not_found_text",
}


class InvalidAdmissionRatingConfig(ValueError):
    def __init__(self, message: str, *, path: str = "config") -> None:
        super().__init__(message)
        self.path = path


def _text(value: Any, *, path: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidAdmissionRatingConfig("Text cannot be empty", path=path)
    result = value.strip()
    if len(result) > maximum:
        raise InvalidAdmissionRatingConfig(f"Text exceeds {maximum} characters", path=path)
    if _MARKUP_RE.search(result):
        raise InvalidAdmissionRatingConfig("Markup is not allowed", path=path)
    return result


@dataclass(frozen=True, slots=True)
class AdmissionRatingConfig:
    provider: str
    admission_year: int
    polling_interval_seconds: int
    notifications_enabled: bool
    title: str
    subtitle: str
    lookup_label: str
    not_found_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        return {
            "admission_year": self.admission_year,
            "notifications_enabled": self.notifications_enabled,
            "title": self.title,
            "subtitle": self.subtitle,
            "lookup_label": self.lookup_label,
            "not_found_text": self.not_found_text,
        }


def parse_admission_rating_config(value: dict[str, Any]) -> AdmissionRatingConfig:
    if not isinstance(value, dict):
        raise InvalidAdmissionRatingConfig("Configuration must be an object")
    unknown = set(value) - _ALLOWED_KEYS
    missing = _ALLOWED_KEYS - set(value)
    if unknown or missing:
        fields = unknown or missing
        kind = "Unknown" if unknown else "Missing"
        raise InvalidAdmissionRatingConfig(f"{kind} fields: {', '.join(sorted(fields))}")
    if value["provider"] != "rut_admission":
        raise InvalidAdmissionRatingConfig("Unsupported provider", path="config.provider")
    year = value["admission_year"]
    current_year = datetime.now(tz=UTC).year
    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not current_year - 1 <= year <= current_year + 2
    ):
        raise InvalidAdmissionRatingConfig(
            "Admission year is outside the supported range", path="config.admission_year"
        )
    interval = value["polling_interval_seconds"]
    if not isinstance(interval, int) or isinstance(interval, bool) or not 300 <= interval <= 86_400:
        raise InvalidAdmissionRatingConfig(
            "Polling interval must be between 300 and 86400 seconds", path="config.polling_interval_seconds"
        )
    notifications = value["notifications_enabled"]
    if not isinstance(notifications, bool):
        raise InvalidAdmissionRatingConfig(
            "notifications_enabled must be boolean", path="config.notifications_enabled"
        )
    return AdmissionRatingConfig(
        provider="rut_admission",
        admission_year=year,
        polling_interval_seconds=interval,
        notifications_enabled=notifications,
        title=_text(value["title"], path="config.title", maximum=200),
        subtitle=_text(value["subtitle"], path="config.subtitle", maximum=500),
        lookup_label=_text(value["lookup_label"], path="config.lookup_label", maximum=120),
        not_found_text=_text(value["not_found_text"], path="config.not_found_text", maximum=500),
    )


def validate_admission_rating_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_admission_rating_config(value).to_dict()


def project_admission_rating_public_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_admission_rating_config(value).public_dict()
