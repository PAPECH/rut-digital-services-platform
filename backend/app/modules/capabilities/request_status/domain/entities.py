from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RequestStatusState:
    id: int | None
    bot_instance_id: int
    installation_id: int
    request_number: str
    request_number_hash: str
    last_status: str | None
    checked_at: datetime
    source_revision: int = 0


@dataclass(frozen=True, slots=True)
class RequestStatusSubscription:
    id: int | None
    bot_instance_id: int
    installation_id: int
    user_id: int
    request_number: str
    request_number_hash: str
    is_active: bool = True
