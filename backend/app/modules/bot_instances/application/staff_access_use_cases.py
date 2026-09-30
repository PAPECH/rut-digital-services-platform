from __future__ import annotations

from ..domain.staff_access import BotStaffAccess, StaffIdentity
from ..domain.staff_access_repository import StaffAccessRepository
from .staff_access_commands import (
    GrantStaffAccessCommand,
    RevokeStaffAccessCommand,
    UpdateStaffAccessCommand,
)


class StaffAccessAlreadyExists(RuntimeError):
    pass


class StaffAccessNotFound(RuntimeError):
    pass


class StaffIdentityInactive(RuntimeError):
    pass


class CannotRemoveOwnStaffManagement(RuntimeError):
    pass


class ListBotStaffAccess:
    def __init__(self, repository: StaffAccessRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[BotStaffAccess]:
        return self._repository.list_for_bot(bot_instance_id)


class GrantBotStaffAccess:
    def __init__(self, repository: StaffAccessRepository) -> None:
        self._repository = repository

    def execute(self, command: GrantStaffAccessCommand) -> BotStaffAccess:
        staff = self._repository.find_staff_by_max_user_id(command.max_user_id.strip())
        if staff is None:
            staff = self._repository.add_staff(
                StaffIdentity(
                    id=None,
                    max_user_id=command.max_user_id,
                    full_name=command.full_name,
                    role=command.role,
                )
            )
        if not staff.is_active:
            raise StaffIdentityInactive(command.max_user_id)
        if staff.id is None:
            raise RuntimeError("Staff identity was not persisted")
        if self._repository.get_by_staff(command.bot_instance_id, staff.id) is not None:
            raise StaffAccessAlreadyExists(command.max_user_id)
        return self._repository.add_access(
            command.bot_instance_id,
            staff.id,
            command.permissions,
        )


class UpdateBotStaffAccess:
    def __init__(self, repository: StaffAccessRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateStaffAccessCommand) -> BotStaffAccess:
        access = self._repository.get(command.bot_instance_id, command.access_id)
        if access is None:
            raise StaffAccessNotFound(str(command.access_id))
        if access.staff.id == command.actor_admin_id and not command.permissions.can_manage_staff:
            raise CannotRemoveOwnStaffManagement
        return self._repository.update_permissions(access, command.permissions)


class RevokeBotStaffAccess:
    def __init__(self, repository: StaffAccessRepository) -> None:
        self._repository = repository

    def execute(self, command: RevokeStaffAccessCommand) -> None:
        access = self._repository.get(command.bot_instance_id, command.access_id)
        if access is None:
            raise StaffAccessNotFound(str(command.access_id))
        if access.staff.id == command.actor_admin_id:
            raise CannotRemoveOwnStaffManagement
        self._repository.delete(access)

