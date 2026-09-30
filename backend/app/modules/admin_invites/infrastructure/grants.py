from __future__ import annotations

from sqlalchemy.orm import Session

from ...bot_instances.application.staff_access_commands import GrantStaffAccessCommand
from ...bot_instances.application.staff_access_use_cases import (
    GrantBotStaffAccess,
    StaffAccessAlreadyExists,
    StaffIdentityInactive,
)
from ...bot_instances.domain.staff_access import StaffPermissions
from ...bot_instances.infrastructure.staff_access_repository import (
    SqlAlchemyStaffAccessRepository,
)
from ...platform_admins.application.commands import EnsurePlatformAdminCommand
from ...platform_admins.application.use_cases import EnsurePlatformAdmin
from ...platform_admins.infrastructure.repository import SqlAlchemyPlatformAdminRepository
from ..application.ports import GrantOutcome, InviteeInactive
from ..domain.entities import InviteStaffRole


class UseCaseInviteGrants:
    def __init__(self, session: Session) -> None:
        self._session = session

    def grant_platform_admin(self, max_user_id: str, full_name: str) -> GrantOutcome:
        result = EnsurePlatformAdmin(SqlAlchemyPlatformAdminRepository(self._session)).execute(
            EnsurePlatformAdminCommand(max_user_id=max_user_id, full_name=full_name)
        )
        if result.identity.id is None:
            raise RuntimeError("Platform administrator was not persisted")
        return GrantOutcome(admin_id=result.identity.id, created=result.created)

    def grant_bot_staff(
        self,
        bot_instance_id: int,
        max_user_id: str,
        full_name: str,
        role: InviteStaffRole,
        permissions: StaffPermissions,
    ) -> GrantOutcome:
        repository = SqlAlchemyStaffAccessRepository(self._session)
        existing = repository.find_staff_by_max_user_id(max_user_id)
        try:
            access = GrantBotStaffAccess(repository).execute(
                GrantStaffAccessCommand(
                    bot_instance_id=bot_instance_id,
                    max_user_id=max_user_id,
                    full_name=full_name,
                    role=role,
                    permissions=permissions,
                )
            )
        except StaffIdentityInactive as exc:
            raise InviteeInactive(max_user_id) from exc
        except StaffAccessAlreadyExists:
            if existing is None or existing.id is None:
                raise
            return GrantOutcome(admin_id=existing.id, created=False)
        if access.staff.id is None:
            raise RuntimeError("Staff identity was not persisted")
        return GrantOutcome(admin_id=access.staff.id, created=existing is None)
