from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_MARKUP_RE = re.compile(r"<[^>]+>")
_SHEET_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
_RANGE_RE = re.compile(r"^[A-Za-zА-Яа-я0-9 _'!:$-]{1,120}$")
_ALLOWED_CREDENTIAL_REFS = {"mock", "legacy_google_sheets"}
_ALLOWED_KEYS = {
    "provider",
    "credential_ref",
    "spreadsheet_id",
    "sheet_range",
    "request_number_column",
    "status_column",
    "normalization",
    "polling_interval_seconds",
    "notifications_enabled",
    "title",
    "subtitle",
    "lookup_label",
    "not_found_text",
}


class InvalidRequestStatusConfig(ValueError):
    def __init__(self, message: str, *, path: str = "config") -> None:
        super().__init__(message)
        self.path = path


def _text(value: Any, *, path: str, maximum: int, required: bool = True) -> str:
    if not isinstance(value, str):
        raise InvalidRequestStatusConfig("Expected text", path=path)
    normalized = value.strip()
    if required and not normalized:
        raise InvalidRequestStatusConfig("Text cannot be empty", path=path)
    if len(normalized) > maximum:
        raise InvalidRequestStatusConfig(f"Text exceeds {maximum} characters", path=path)
    if _MARKUP_RE.search(normalized):
        raise InvalidRequestStatusConfig("Markup is not allowed", path=path)
    return normalized


@dataclass(frozen=True, slots=True)
class RequestStatusConfig:
    provider: str
    credential_ref: str
    spreadsheet_id: str
    sheet_range: str
    request_number_column: int
    status_column: int
    normalization: str
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
            "title": self.title,
            "subtitle": self.subtitle,
            "lookup_label": self.lookup_label,
            "not_found_text": self.not_found_text,
            "notifications_enabled": self.notifications_enabled,
        }


def parse_request_status_config(value: dict[str, Any]) -> RequestStatusConfig:
    if not isinstance(value, dict):
        raise InvalidRequestStatusConfig("Configuration must be an object")
    unknown = set(value) - _ALLOWED_KEYS
    missing = _ALLOWED_KEYS - set(value)
    if unknown:
        raise InvalidRequestStatusConfig(
            f"Unknown fields: {', '.join(sorted(unknown))}",
            path="config",
        )
    if missing:
        raise InvalidRequestStatusConfig(
            f"Missing fields: {', '.join(sorted(missing))}",
            path="config",
        )
    if value["provider"] != "google_sheets":
        raise InvalidRequestStatusConfig("Unsupported provider", path="config.provider")
    credential_ref = _text(value["credential_ref"], path="config.credential_ref", maximum=80)
    if credential_ref not in _ALLOWED_CREDENTIAL_REFS:
        raise InvalidRequestStatusConfig(
            "Credential reference is not deployment-allowlisted",
            path="config.credential_ref",
        )
    spreadsheet_id = _text(value["spreadsheet_id"], path="config.spreadsheet_id", maximum=200)
    if credential_ref != "mock" and not _SHEET_ID_RE.fullmatch(spreadsheet_id):
        raise InvalidRequestStatusConfig(
            "Invalid spreadsheet id",
            path="config.spreadsheet_id",
        )
    sheet_range = _text(value["sheet_range"], path="config.sheet_range", maximum=120)
    if not _RANGE_RE.fullmatch(sheet_range):
        raise InvalidRequestStatusConfig("Invalid sheet range", path="config.sheet_range")
    number_column = value["request_number_column"]
    status_column = value["status_column"]
    if not isinstance(number_column, int) or isinstance(number_column, bool) or not 0 <= number_column <= 50:
        raise InvalidRequestStatusConfig(
            "Request-number column must be between 0 and 50",
            path="config.request_number_column",
        )
    if not isinstance(status_column, int) or isinstance(status_column, bool) or not 0 <= status_column <= 50:
        raise InvalidRequestStatusConfig(
            "Status column must be between 0 and 50",
            path="config.status_column",
        )
    if number_column == status_column:
        raise InvalidRequestStatusConfig(
            "Request-number and status columns must differ",
            path="config.status_column",
        )
    if value["normalization"] not in {"trim", "compact"}:
        raise InvalidRequestStatusConfig(
            "Unsupported normalization",
            path="config.normalization",
        )
    interval = value["polling_interval_seconds"]
    if not isinstance(interval, int) or isinstance(interval, bool) or not 60 <= interval <= 86_400:
        raise InvalidRequestStatusConfig(
            "Polling interval must be between 60 and 86400 seconds",
            path="config.polling_interval_seconds",
        )
    notifications_enabled = value["notifications_enabled"]
    if not isinstance(notifications_enabled, bool):
        raise InvalidRequestStatusConfig(
            "notifications_enabled must be boolean",
            path="config.notifications_enabled",
        )
    return RequestStatusConfig(
        provider="google_sheets",
        credential_ref=credential_ref,
        spreadsheet_id=spreadsheet_id,
        sheet_range=sheet_range,
        request_number_column=number_column,
        status_column=status_column,
        normalization=value["normalization"],
        polling_interval_seconds=interval,
        notifications_enabled=notifications_enabled,
        title=_text(value["title"], path="config.title", maximum=200),
        subtitle=_text(value["subtitle"], path="config.subtitle", maximum=500),
        lookup_label=_text(value["lookup_label"], path="config.lookup_label", maximum=120),
        not_found_text=_text(value["not_found_text"], path="config.not_found_text", maximum=500),
    )


def validate_request_status_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_request_status_config(value).to_dict()


def project_request_status_public_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_request_status_config(value).public_dict()
