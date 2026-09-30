from __future__ import annotations

from dataclasses import dataclass, replace

from ..domain.entities import GlobalAdminIdentity, GlobalAdminRole
from ..domain.repository import PlatformAdminRepository
from .commands import EnsurePlatformAdminCommand


@dataclass(frozen=True, slots=True)
class EnsurePlatformAdminResult:
    identity: GlobalAdminIdentity
    created: bool
    previous_role: GlobalAdminRole | None
    reactivated: bool


class EnsurePlatformAdmin:
    def __init__(self, repository: PlatformAdminRepository) -> None:
        self._repository = repository

    def execute(self, command: EnsurePlatformAdminCommand) -> EnsurePlatformAdminResult:
        candidate = GlobalAdminIdentity(
            id=None,
            max_user_id=command.max_user_id,
            full_name=command.full_name,
            role="platform_admin",
            is_active=True,
        )
        existing = self._repository.find_by_max_user_id(candidate.max_user_id)
        if existing is None:
            return EnsurePlatformAdminResult(
                identity=self._repository.add(candidate),
                created=True,
                previous_role=None,
                reactivated=False,
            )

        updated = replace(
            existing,
            full_name=candidate.full_name,
            role="platform_admin",
            is_active=True,
        )
        return EnsurePlatformAdminResult(
            identity=self._repository.update(updated),
            created=False,
            previous_role=existing.role,
            reactivated=not existing.is_active,
        )


class ListPlatformAdmins:
    def __init__(self, repository: PlatformAdminRepository) -> None:
        self._repository = repository

    def execute(self) -> list[GlobalAdminIdentity]:
        return self._repository.list_platform_admins()
