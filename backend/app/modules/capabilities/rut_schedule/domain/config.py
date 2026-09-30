from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_MARKUP_RE = re.compile(r"<[^>]+>")
_ALLOWED_KEYS = {
    "provider",
    "title",
    "subtitle",
    "group_cache_ttl_seconds",
    "hierarchy_sync_interval_seconds",
    "night_auto_sync_enabled",
}
# `night_auto_sync_enabled` is allowed but not required in the input: it's written only from the
# platform-admin panel (see Task 045), never rendered by the bot-admin editor, and every
# installation configured before this field existed has a stored `config` JSON that simply lacks
# it. Requiring it like the other keys would make every such installation fail validation (and
# therefore its browse view / nightly sync) the moment this ships, before anyone re-saves it --
# so a missing value defaults to `True` at parse time instead. `to_dict()` then always emits the
# resolved value, so the very next save from either surface persists it explicitly.
_REQUIRED_KEYS = _ALLOWED_KEYS - {"night_auto_sync_enabled"}


class InvalidRutScheduleConfig(ValueError):
    def __init__(self, message: str, *, path: str = "config") -> None:
        super().__init__(message)
        self.path = path


def _text(value: Any, *, path: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRutScheduleConfig("Text cannot be empty", path=path)
    result = value.strip()
    if len(result) > maximum:
        raise InvalidRutScheduleConfig(f"Text exceeds {maximum} characters", path=path)
    if _MARKUP_RE.search(result):
        raise InvalidRutScheduleConfig("Markup is not allowed", path=path)
    return result


def _bounded_int(value: Any, *, path: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise InvalidRutScheduleConfig(f"Must be an integer between {minimum} and {maximum}", path=path)
    return value


@dataclass(frozen=True, slots=True)
class RutScheduleConfig:
    provider: str
    title: str
    subtitle: str
    group_cache_ttl_seconds: int
    hierarchy_sync_interval_seconds: int
    night_auto_sync_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        return {"title": self.title, "subtitle": self.subtitle}


def _optional_bool(value: Any, *, path: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise InvalidRutScheduleConfig("Must be a boolean", path=path)
    return value


def parse_rut_schedule_config(value: dict[str, Any]) -> RutScheduleConfig:
    if not isinstance(value, dict):
        raise InvalidRutScheduleConfig("Configuration must be an object")
    unknown = set(value) - _ALLOWED_KEYS
    missing = _REQUIRED_KEYS - set(value)
    if unknown or missing:
        fields = unknown or missing
        kind = "Unknown" if unknown else "Missing"
        raise InvalidRutScheduleConfig(f"{kind} fields: {', '.join(sorted(fields))}")
    if value["provider"] != "miit_timetable":
        raise InvalidRutScheduleConfig("Unsupported provider", path="config.provider")
    return RutScheduleConfig(
        provider="miit_timetable",
        title=_text(value["title"], path="config.title", maximum=200),
        subtitle=_text(value["subtitle"], path="config.subtitle", maximum=500),
        group_cache_ttl_seconds=_bounded_int(
            value["group_cache_ttl_seconds"],
            path="config.group_cache_ttl_seconds",
            minimum=60,
            maximum=86_400,
        ),
        hierarchy_sync_interval_seconds=_bounded_int(
            value["hierarchy_sync_interval_seconds"],
            path="config.hierarchy_sync_interval_seconds",
            minimum=300,
            maximum=604_800,
        ),
        night_auto_sync_enabled=_optional_bool(
            value.get("night_auto_sync_enabled"),
            path="config.night_auto_sync_enabled",
            default=True,
        ),
    )


def validate_rut_schedule_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_rut_schedule_config(value).to_dict()


def project_rut_schedule_public_config(value: dict[str, Any]) -> dict[str, Any]:
    return parse_rut_schedule_config(value).public_dict()
