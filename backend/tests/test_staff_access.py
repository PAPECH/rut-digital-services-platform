from dataclasses import replace

import pytest

from app.modules.bot_instances.application.staff_access_commands import (
    RevokeStaffAccessCommand,
    UpdateStaffAccessCommand,
)
from app.modules.bot_instances.application.staff_access_use_cases import (
    CannotRemoveOwnStaffManagement,
    RevokeBotStaffAccess,
    StaffAccessNotFound,
    UpdateBotStaffAccess,
)
from app.modules.bot_instances.domain.staff_access import (
    BotStaffAccess,
    StaffIdentity,
    StaffPermissions,
)


class InMemoryStaffAccessRepository:
    def __init__(self, access: BotStaffAccess) -> None:
        self.access = access
        self.deleted = False

    def get(self, bot_instance_id: int, access_id: int) -> BotStaffAccess | None:
        if self.access.bot_instance_id == bot_instance_id and self.access.id == access_id:
            return self.access
        return None

    def update_permissions(
        self, access: BotStaffAccess, permissions: StaffPermissions
    ) -> BotStaffAccess:
        self.access = replace(access, permissions=permissions)
        return self.access

    def delete(self, access: BotStaffAccess) -> None:
        self.deleted = True


def _access() -> BotStaffAccess:
    return BotStaffAccess(
        id=7,
        bot_instance_id=2,
        staff=StaffIdentity(
            id=11,
            max_user_id="max-11",
            full_name="Иван Иванов",
            role="admin",
        ),
        permissions=StaffPermissions(can_manage_staff=True),
    )


def test_access_from_another_bot_cannot_be_revoked() -> None:
    repository = InMemoryStaffAccessRepository(_access())

    with pytest.raises(StaffAccessNotFound):
        RevokeBotStaffAccess(repository).execute(
            RevokeStaffAccessCommand(bot_instance_id=1, access_id=7, actor_admin_id=10)
        )

    assert repository.deleted is False


def test_manager_cannot_remove_own_staff_permission() -> None:
    repository = InMemoryStaffAccessRepository(_access())

    with pytest.raises(CannotRemoveOwnStaffManagement):
        UpdateBotStaffAccess(repository).execute(
            UpdateStaffAccessCommand(
                bot_instance_id=2,
                access_id=7,
                actor_admin_id=11,
                permissions=StaffPermissions(can_manage_staff=False),
            )
        )

