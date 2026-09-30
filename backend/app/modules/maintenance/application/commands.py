from dataclasses import dataclass
from datetime import datetime

from ..domain.policies import MaintenanceMode


@dataclass(frozen=True, slots=True)
class SetMaintenanceCommand:
    scope_key: str
    bot_instance_id: int | None
    mode: MaintenanceMode
    title: str
    message: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    retry_after_seconds: int | None = None
    allow_admin: bool = True
    updated_by: int | None = None
