from __future__ import annotations

from dataclasses import dataclass

from ..domain.staff_access import StaffPermissions, StaffRole


@dataclass(frozen=True, slots=True)
class GrantStaffAccessCommand:
    bot_instance_id: int
    max_user_id: str
    full_name: str
    role: StaffRole
    permissions: StaffPermissions


@dataclass(frozen=True, slots=True)
class UpdateStaffAccessCommand:
    bot_instance_id: int
    access_id: int
    actor_admin_id: int
    permissions: StaffPermissions


@dataclass(frozen=True, slots=True)
class RevokeStaffAccessCommand:
    bot_instance_id: int
    access_id: int
    actor_admin_id: int

