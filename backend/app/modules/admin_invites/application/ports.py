from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...bot_instances.domain.staff_access import StaffPermissions
from ..domain.entities import InviteStaffRole


class InviteTokenCodec(Protocol):
    def generate(self) -> str: ...

    def digest(self, raw_token: str) -> str: ...


@dataclass(frozen=True, slots=True)
class GrantOutcome:
    admin_id: int
    created: bool


class InviteeInactive(RuntimeError):
    pass


class InviteGrants(Protocol):
    def grant_platform_admin(self, max_user_id: str, full_name: str) -> GrantOutcome: ...

    def grant_bot_staff(
        self,
        bot_instance_id: int,
        max_user_id: str,
        full_name: str,
        role: InviteStaffRole,
        permissions: StaffPermissions,
    ) -> GrantOutcome: ...
