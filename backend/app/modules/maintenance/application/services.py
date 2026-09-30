from __future__ import annotations

from datetime import datetime

from ..domain.policies import MaintenancePolicy, resolve_effective_policy
from ..domain.repositories import MaintenanceRepository
from .commands import SetMaintenanceCommand


class GetEffectiveMaintenance:
    def __init__(self, repository: MaintenanceRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, *, now: datetime | None = None) -> MaintenancePolicy | None:
        return resolve_effective_policy(
            self._repository.get("global"),
            self._repository.get(f"bot:{bot_instance_id}"),
            now=now,
        )


class SetMaintenance:
    def __init__(self, repository: MaintenanceRepository) -> None:
        self._repository = repository

    def execute(self, command: SetMaintenanceCommand) -> MaintenancePolicy:
        if command.ends_at and command.starts_at and command.ends_at <= command.starts_at:
            raise ValueError("Maintenance end must be later than start")
        if command.retry_after_seconds is not None and command.retry_after_seconds < 0:
            raise ValueError("Retry-after cannot be negative")
        return self._repository.save(
            MaintenancePolicy(
                scope_key=command.scope_key,
                bot_instance_id=command.bot_instance_id,
                mode=command.mode,
                title=command.title.strip(),
                message=command.message.strip(),
                starts_at=command.starts_at,
                ends_at=command.ends_at,
                retry_after_seconds=command.retry_after_seconds,
                allow_admin=command.allow_admin,
            ),
            updated_by=command.updated_by,
        )
