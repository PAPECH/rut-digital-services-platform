from __future__ import annotations

from typing import Protocol

from .staff_access import BotStaffAccess, StaffIdentity, StaffPermissions


class StaffAccessRepository(Protocol):
    def list_for_bot(self, bot_instance_id: int) -> list[BotStaffAccess]: ...

    def get(self, bot_instance_id: int, access_id: int) -> BotStaffAccess | None: ...

    def get_by_staff(self, bot_instance_id: int, staff_id: int) -> BotStaffAccess | None: ...

    def find_staff_by_max_user_id(self, max_user_id: str) -> StaffIdentity | None: ...

    def add_staff(self, staff: StaffIdentity) -> StaffIdentity: ...

    def add_access(
        self,
        bot_instance_id: int,
        staff_id: int,
        permissions: StaffPermissions,
    ) -> BotStaffAccess: ...

    def update_permissions(
        self,
        access: BotStaffAccess,
        permissions: StaffPermissions,
    ) -> BotStaffAccess: ...

    def delete(self, access: BotStaffAccess) -> None: ...

