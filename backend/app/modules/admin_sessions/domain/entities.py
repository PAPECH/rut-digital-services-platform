from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AdminRefreshSession:
    id: int | None
    admin_id: int
    family_id: str
    token_hash: str
    expires_at: datetime
    absolute_expires_at: datetime
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    replaced_by_id: int | None = None
    user_agent: str | None = None
    ip: str | None = None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at or now >= self.absolute_expires_at

    @property
    def was_rotated(self) -> bool:
        return self.replaced_by_id is not None
