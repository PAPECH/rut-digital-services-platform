from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigureCapabilityCommand:
    bot_instance_id: int
    capability_key: str
    config: dict[str, Any]
    expected_revision: int
    configured_by: int | None
    create_if_missing: bool = False
    require_enabled: bool = False


@dataclass(frozen=True, slots=True)
class SetCapabilityEnabledCommand:
    bot_instance_id: int
    capability_key: str
    enabled: bool
    changed_by: int | None
