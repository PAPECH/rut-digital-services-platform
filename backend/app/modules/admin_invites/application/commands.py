from __future__ import annotations

from dataclasses import dataclass

from ...bot_instances.domain.staff_access import StaffPermissions
from ..domain.entities import InviteKind, InviteStaffRole


@dataclass(frozen=True, slots=True)
class CreateAdminInviteCommand:
    kind: InviteKind
    bot_instance_id: int | None
    full_name: str
    staff_role: InviteStaffRole | None
    permissions: StaffPermissions | None
    ttl_hours: int
    max_uses: int
    created_by_admin_id: int | None


@dataclass(frozen=True, slots=True)
class RevokeAdminInviteCommand:
    invite_id: int
    kind: InviteKind
    bot_instance_id: int | None


@dataclass(frozen=True, slots=True)
class RedeemAdminInviteCommand:
    raw_token: str
    max_user_id: str
