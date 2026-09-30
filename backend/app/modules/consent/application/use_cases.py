from __future__ import annotations

from datetime import datetime

from ..domain.business_days import add_business_days
from ..domain.entities import ConsentEventType, ConsentState
from ..domain.repositories import ConsentRepository

REVOKE_GRACE_BUSINESS_DAYS = 10


class CheckConsentGate:
    """Read-only gate check -- invoked explicitly at the top of any entry point that would
    otherwise create a `User` row or process a person's content (message ingress, mini-app
    bootstrap). Not a bare FastAPI `Depends()`: it needs the *external* identity from the
    request payload, before any `User` row or principal exists."""

    def __init__(self, repo: ConsentRepository) -> None:
        self._repo = repo

    def execute(self, external_user_id: str, system: str) -> bool:
        state = self._repo.get_by_external(external_user_id, system)
        return state is not None and state.is_active


class AcceptConsent:
    def __init__(self, repo: ConsentRepository) -> None:
        self._repo = repo

    def execute(
        self,
        *,
        external_user_id: str,
        system: str,
        user_id: int | None,
        policy_version: str | None,
        now: datetime,
    ) -> ConsentState:
        current = self._repo.get_by_external(external_user_id, system)
        if current is not None and current.is_active:
            # Idempotent: already consented, nothing changes, no new event.
            return current
        state = self._repo.upsert_given(
            external_user_id=external_user_id,
            system=system,
            user_id=user_id,
            policy_version=policy_version,
            now=now,
        )
        self._repo.append_event(
            state.id, ConsentEventType.given, occurred_at=now, policy_version=policy_version
        )
        return state


class RevokeConsent:
    def __init__(self, repo: ConsentRepository) -> None:
        self._repo = repo

    def execute(self, *, external_user_id: str, system: str, now: datetime) -> ConsentState | None:
        current = self._repo.get_by_external(external_user_id, system)
        if current is None or current.revoked_at is not None:
            # Nothing to revoke, or already revoked -- idempotent, does not push the
            # deletion date further out.
            return current
        deletion_due_at = add_business_days(now, REVOKE_GRACE_BUSINESS_DAYS)
        state = self._repo.set_revoked(current.id, revoked_at=now, deletion_due_at=deletion_due_at)
        self._repo.append_event(
            state.id, ConsentEventType.revoked, occurred_at=now, policy_version=state.policy_version
        )
        return state


class GetConsentStatus:
    def __init__(self, repo: ConsentRepository) -> None:
        self._repo = repo

    def execute(self, external_user_id: str, system: str) -> ConsentState | None:
        return self._repo.get_by_external(external_user_id, system)
