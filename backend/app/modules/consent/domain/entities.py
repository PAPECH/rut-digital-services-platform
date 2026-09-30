from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ConsentEventType(StrEnum):
    given = "given"
    revoked = "revoked"
    deletion_executed = "deletion_executed"


@dataclass(frozen=True, slots=True)
class ConsentState:
    """Current consent cycle for one real-world identity.

    Keyed by (external_user_id, system) rather than `user_id` -- `user_id` goes null once
    the identity is erased (Task 064), while this row survives as the durable compliance
    record across repeated give -> revoke -> delete cycles for the same person.
    """

    id: int | None
    user_id: int | None
    external_user_id: str
    system: str
    given_at: datetime | None
    revoked_at: datetime | None
    deletion_due_at: datetime | None
    deleted_at: datetime | None
    policy_version: str | None

    @property
    def is_active(self) -> bool:
        """True once consent was given and not since revoked.

        Deliberately ignores `deleted_at`: after a completed erasure cycle that was never
        followed by a fresh accept, `revoked_at` is still set (never cleared by the sweep),
        so this already reads False without needing `deleted_at` in the condition.
        """
        return self.given_at is not None and self.revoked_at is None


@dataclass(frozen=True, slots=True)
class ConsentEvent:
    id: int | None
    consent_id: int
    event_type: ConsentEventType
    occurred_at: datetime
    policy_version: str | None
