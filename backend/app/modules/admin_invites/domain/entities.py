from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ...bot_instances.domain.staff_access import StaffPermissions

InviteKind = Literal["platform", "bot_staff"]
InviteStaffRole = Literal["employee", "admin"]
InviteStatus = Literal["active", "expired", "exhausted", "revoked"]

MAX_INVITE_USES = 100
MAX_INVITE_TTL_HOURS = 720


@dataclass(frozen=True, slots=True)
class AdminInvite:
    id: int | None
    kind: InviteKind
    bot_instance_id: int | None
    full_name: str
    staff_role: InviteStaffRole | None
    permissions: StaffPermissions | None
    max_uses: int
    used_count: int
    expires_at: datetime
    created_by_admin_id: int | None
    created_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        full_name = " ".join(self.full_name.split())
        if not full_name:
            raise ValueError("Full name is required")
        if len(full_name) > 200:
            raise ValueError("Full name is too long")
        object.__setattr__(self, "full_name", full_name)

        if self.kind == "platform":
            if self.bot_instance_id is not None or self.staff_role or self.permissions:
                raise ValueError("A platform invite cannot carry bot access")
        elif self.bot_instance_id is None or self.staff_role is None or self.permissions is None:
            raise ValueError("A bot staff invite needs a bot, a role and permissions")

        if not 1 <= self.max_uses <= MAX_INVITE_USES:
            raise ValueError(f"Max uses must be between 1 and {MAX_INVITE_USES}")
        if not 0 <= self.used_count <= self.max_uses:
            raise ValueError("Used count is out of range")

    def status(self, now: datetime) -> InviteStatus:
        if self.revoked_at is not None:
            return "revoked"
        if self.used_count >= self.max_uses:
            return "exhausted"
        if now >= self.expires_at:
            return "expired"
        return "active"
