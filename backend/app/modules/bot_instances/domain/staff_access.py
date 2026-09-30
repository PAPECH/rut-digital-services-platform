from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StaffRole = Literal["employee", "admin", "platform_admin"]


@dataclass(frozen=True, slots=True)
class StaffPermissions:
    can_process_submissions: bool = True
    can_manage_content: bool = False
    can_manage_forms: bool = False
    can_manage_staff: bool = False
    can_manage_maintenance: bool = False
    can_manage_capabilities: bool = False
    can_manage_campaigns: bool = False
    can_manage_form_tests: bool = False


@dataclass(frozen=True, slots=True)
class StaffIdentity:
    id: int | None
    max_user_id: str
    full_name: str
    role: StaffRole
    is_active: bool = True

    def __post_init__(self) -> None:
        max_user_id = self.max_user_id.strip()
        full_name = self.full_name.strip()
        if not max_user_id or not full_name:
            raise ValueError("MAX user ID and full name are required")
        object.__setattr__(self, "max_user_id", max_user_id)
        object.__setattr__(self, "full_name", full_name)


@dataclass(frozen=True, slots=True)
class BotStaffAccess:
    id: int | None
    bot_instance_id: int
    staff: StaffIdentity
    permissions: StaffPermissions

