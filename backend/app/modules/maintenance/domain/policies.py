from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class MaintenanceMode(StrEnum):
    off = "off"
    informational = "informational"
    read_only = "read_only"
    full_stop = "full_stop"


@dataclass(frozen=True, slots=True)
class MaintenancePolicy:
    scope_key: str
    bot_instance_id: int | None
    mode: MaintenanceMode = MaintenanceMode.off
    title: str = ""
    message: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    retry_after_seconds: int | None = None
    allow_admin: bool = True

    def is_effective(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(tz=timezone.utc)
        if self.mode == MaintenanceMode.off:
            return False
        if self.starts_at and current < self.starts_at:
            return False
        return not (self.ends_at and current >= self.ends_at)

    @property
    def blocks_user_writes(self) -> bool:
        return self.mode in (MaintenanceMode.read_only, MaintenanceMode.full_stop)

    @property
    def blocks_user_access(self) -> bool:
        return self.mode == MaintenanceMode.full_stop


def resolve_effective_policy(
    global_policy: MaintenancePolicy | None,
    bot_policy: MaintenancePolicy | None,
    *,
    now: datetime | None = None,
) -> MaintenancePolicy | None:
    if global_policy and global_policy.is_effective(now):
        return global_policy
    if bot_policy and bot_policy.is_effective(now):
        return bot_policy
    return None
