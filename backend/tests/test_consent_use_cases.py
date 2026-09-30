"""Unit tests for modules/consent's domain + application logic (Task 064) -- pure Python,
no DB, mirrors this repo's existing unit-test convention (see tests/conftest.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.consent.application.use_cases import (
    REVOKE_GRACE_BUSINESS_DAYS,
    AcceptConsent,
    CheckConsentGate,
    RevokeConsent,
)
from app.modules.consent.domain.business_days import add_business_days
from app.modules.consent.domain.entities import ConsentEventType, ConsentState


class FakeConsentRepository:
    """In-memory stand-in for the ConsentRepository protocol, keyed like the real table:
    by (external_user_id, system), not by id."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], ConsentState] = {}
        self.events: list[tuple[int, ConsentEventType, datetime, str | None]] = []
        self._next_id = 1

    def get_by_external(self, external_user_id: str, system: str) -> ConsentState | None:
        return self._by_key.get((external_user_id, system))

    def upsert_given(self, *, external_user_id, system, user_id, policy_version, now):
        key = (external_user_id, system)
        current = self._by_key.get(key)
        state = ConsentState(
            id=current.id if current else self._next_id,
            user_id=user_id if user_id is not None else (current.user_id if current else None),
            external_user_id=external_user_id,
            system=system,
            given_at=now,
            revoked_at=None,
            deletion_due_at=None,
            deleted_at=None,
            policy_version=policy_version,
        )
        if current is None:
            self._next_id += 1
        self._by_key[key] = state
        return state

    def set_revoked(self, consent_id, *, revoked_at, deletion_due_at):
        for key, state in self._by_key.items():
            if state.id == consent_id:
                updated = ConsentState(
                    id=state.id,
                    user_id=state.user_id,
                    external_user_id=state.external_user_id,
                    system=state.system,
                    given_at=state.given_at,
                    revoked_at=revoked_at,
                    deletion_due_at=deletion_due_at,
                    deleted_at=state.deleted_at,
                    policy_version=state.policy_version,
                )
                self._by_key[key] = updated
                return updated
        raise LookupError(consent_id)

    def append_event(self, consent_id, event_type, *, occurred_at, policy_version):
        self.events.append((consent_id, event_type, occurred_at, policy_version))

    def list_due_for_deletion(self, *, now):
        return [
            s.id
            for s in self._by_key.values()
            if s.revoked_at is not None
            and s.deleted_at is None
            and s.deletion_due_at is not None
            and s.deletion_due_at <= now
        ]


# --- business_days -----------------------------------------------------------------------


def test_add_business_days_skips_weekend():
    # Monday 2026-01-05 + 10 business days -> Monday 2026-01-19 (two full weekends skipped).
    start = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)  # Monday
    result = add_business_days(start, 10)
    assert result.weekday() == 0  # Monday
    assert result.date().isoformat() == "2026-01-19"


def test_add_business_days_zero_is_identity():
    start = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    assert add_business_days(start, 0) == start


def test_add_business_days_rejects_negative():
    with pytest.raises(ValueError):
        add_business_days(datetime.now(tz=UTC), -1)


# --- CheckConsentGate ----------------------------------------------------------------------


def test_gate_inactive_for_unknown_identity():
    gate = CheckConsentGate(FakeConsentRepository())
    assert gate.execute("max-1", "max") is False


def test_gate_active_after_accept():
    repo = FakeConsentRepository()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=None, policy_version="v1", now=now
    )
    assert CheckConsentGate(repo).execute("max-1", "max") is True


def test_gate_inactive_immediately_after_revoke():
    repo = FakeConsentRepository()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=now
    )
    RevokeConsent(repo).execute(external_user_id="max-1", system="max", now=now)
    # Revoked = blocked immediately, not "blocked after the grace window" -- the whole
    # point of the 10-business-day window is solely about when *deletion* happens.
    assert CheckConsentGate(repo).execute("max-1", "max") is False


# --- AcceptConsent -------------------------------------------------------------------------


def test_accept_is_idempotent_no_new_event_when_already_active():
    repo = FakeConsentRepository()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=now
    )
    assert len(repo.events) == 1

    AcceptConsent(repo).execute(
        external_user_id="max-1",
        system="max",
        user_id=1,
        policy_version="v1",
        now=now + timedelta(days=1),
    )
    assert len(repo.events) == 1  # no-op, not a second "given" event


def test_re_accept_after_revoke_gets_a_fresh_given_at_not_the_stale_one():
    repo = FakeConsentRepository()
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=t0
    )
    RevokeConsent(repo).execute(external_user_id="max-1", system="max", now=t0 + timedelta(days=1))

    t2 = t0 + timedelta(days=2)
    state = AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=t2
    )
    assert state.given_at == t2
    assert state.revoked_at is None
    assert state.deletion_due_at is None


# --- RevokeConsent -------------------------------------------------------------------------


def test_revoke_sets_deletion_due_at_ten_business_days_out():
    repo = FakeConsentRepository()
    now = datetime(2026, 1, 5, tzinfo=UTC)  # Monday
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=now
    )
    state = RevokeConsent(repo).execute(external_user_id="max-1", system="max", now=now)
    assert state.deletion_due_at == add_business_days(now, REVOKE_GRACE_BUSINESS_DAYS)


def test_revoke_is_idempotent_does_not_push_deletion_date_out():
    repo = FakeConsentRepository()
    t0 = datetime(2026, 1, 5, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="max-1", system="max", user_id=1, policy_version="v1", now=t0
    )
    first = RevokeConsent(repo).execute(external_user_id="max-1", system="max", now=t0)
    second = RevokeConsent(repo).execute(
        external_user_id="max-1", system="max", now=t0 + timedelta(days=3)
    )
    assert second.deletion_due_at == first.deletion_due_at


def test_revoke_unknown_identity_is_a_noop():
    repo = FakeConsentRepository()
    result = RevokeConsent(repo).execute(external_user_id="ghost", system="max", now=datetime.now(tz=UTC))
    assert result is None
    assert repo.events == []


def test_sweep_selection_boundary():
    repo = FakeConsentRepository()
    now = datetime(2026, 1, 15, tzinfo=UTC)
    AcceptConsent(repo).execute(
        external_user_id="due", system="max", user_id=1, policy_version="v1", now=now - timedelta(days=20)
    )
    RevokeConsent(repo).execute(external_user_id="due", system="max", now=now - timedelta(days=15))
    AcceptConsent(repo).execute(
        external_user_id="not-due", system="max", user_id=2, policy_version="v1", now=now - timedelta(days=2)
    )
    RevokeConsent(repo).execute(external_user_id="not-due", system="max", now=now - timedelta(days=1))

    due_ids = repo.list_due_for_deletion(now=now)
    due_state = repo.get_by_external("due", "max")
    not_due_state = repo.get_by_external("not-due", "max")
    assert due_state.id in due_ids
    assert not_due_state.id not in due_ids
