from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .entities import ConsentEventType, ConsentState


class ConsentRepository(Protocol):
    def get_by_external(self, external_user_id: str, system: str) -> ConsentState | None: ...

    def upsert_given(
        self,
        *,
        external_user_id: str,
        system: str,
        user_id: int | None,
        policy_version: str | None,
        now: datetime,
    ) -> ConsentState:
        """Create the row if absent, or update it for a (re-)consent: sets `given_at` if
        unset, clears `revoked_at`/`deletion_due_at`/`deleted_at` -- covers both a first-time
        accept and a fresh cycle after a prior erasure."""
        ...

    def set_revoked(
        self, consent_id: int, *, revoked_at: datetime, deletion_due_at: datetime
    ) -> ConsentState: ...

    def append_event(
        self,
        consent_id: int,
        event_type: ConsentEventType,
        *,
        occurred_at: datetime,
        policy_version: str | None,
    ) -> None: ...

    def list_due_for_deletion(self, *, now: datetime) -> list[int]:
        """Ids of `user_consents` rows past their `deletion_due_at` and not yet deleted."""
        ...
