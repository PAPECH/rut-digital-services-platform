from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

CAPABILITY_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
VIEW_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class InvalidCapability(ValueError):
    pass


class UnknownCapability(LookupError):
    pass


ConfigValidator = Callable[[dict[str, Any]], dict[str, Any]]
PublicConfigProjector = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class CapabilityView:
    key: str
    title: str
    subtitle: str | None
    icon: str
    requires_complete_profile: bool = False

    def __post_init__(self) -> None:
        if not VIEW_KEY_RE.fullmatch(self.key):
            raise InvalidCapability("Invalid capability view key")
        if not self.title.strip() or len(self.title) > 200:
            raise InvalidCapability("Capability view title is required")
        if not self.icon.strip() or len(self.icon) > 80:
            raise InvalidCapability("Capability view icon is required")


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    key: str
    version: str
    name: str
    description: str
    admin_editor_key: str
    views: tuple[CapabilityView, ...]
    validate_config: ConfigValidator = field(repr=False, compare=False)
    public_config: PublicConfigProjector = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not CAPABILITY_KEY_RE.fullmatch(self.key):
            raise InvalidCapability("Invalid capability key")
        if not SEMVER_RE.fullmatch(self.version):
            raise InvalidCapability("Capability version must use semantic versioning")
        if not self.name.strip() or not self.description.strip():
            raise InvalidCapability("Capability name and description are required")
        if not CAPABILITY_KEY_RE.fullmatch(self.admin_editor_key):
            raise InvalidCapability("Invalid capability editor key")
        view_keys = [view.key for view in self.views]
        if not view_keys or len(view_keys) != len(set(view_keys)):
            raise InvalidCapability("Capability views must be non-empty and unique")

    def get_view(self, view_key: str) -> CapabilityView:
        for view in self.views:
            if view.key == view_key:
                return view
        raise UnknownCapability(f"Unknown view {self.key}:{view_key}")


class CapabilityRegistry:
    def __init__(self, descriptors: Iterable[CapabilityDescriptor]) -> None:
        items = tuple(descriptors)
        keys = [item.key for item in items]
        if len(keys) != len(set(keys)):
            raise InvalidCapability("Duplicate capability key")
        self._items = {item.key: item for item in items}

    def list(self) -> tuple[CapabilityDescriptor, ...]:
        return tuple(self._items[key] for key in sorted(self._items))

    def get(self, key: str) -> CapabilityDescriptor:
        try:
            return self._items[key]
        except KeyError as exc:
            raise UnknownCapability(key) from exc


@dataclass(frozen=True, slots=True)
class CapabilityInstallation:
    id: int | None
    bot_instance_id: int
    capability_key: str
    is_enabled: bool = False
    order: int = 0
    config: dict[str, Any] = field(default_factory=dict)
    config_revision: int = 0
    configured_by: int | None = None
    enabled_by: int | None = None
    last_health_status: str = "unconfigured"
    last_health_at: datetime | None = None
    last_health_error_code: str | None = None

    def __post_init__(self) -> None:
        if self.bot_instance_id <= 0:
            raise InvalidCapability("Capability tenant is required")
        if not CAPABILITY_KEY_RE.fullmatch(self.capability_key):
            raise InvalidCapability("Invalid capability key")
        if self.order < 0:
            raise InvalidCapability("Capability order cannot be negative")
        if self.config_revision < 0:
            raise InvalidCapability("Capability config revision cannot be negative")
        if self.last_health_status not in {"unconfigured", "unknown", "healthy", "degraded"}:
            raise InvalidCapability("Invalid capability health status")
