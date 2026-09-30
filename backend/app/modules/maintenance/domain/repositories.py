from __future__ import annotations

from typing import Protocol

from .policies import MaintenancePolicy


class MaintenanceRepository(Protocol):
    def get(self, scope_key: str) -> MaintenancePolicy | None: ...

    def save(self, policy: MaintenancePolicy, *, updated_by: int | None) -> MaintenancePolicy: ...
