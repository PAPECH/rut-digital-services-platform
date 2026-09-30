from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....models.enums import SystemEnum
from ..domain.entities import ConsentEventType, ConsentState
from .models import ConsentEventRecord, UserConsentRecord


def _system_value(record: UserConsentRecord) -> str:
    # A record just constructed in this same call (the "new consent row" branch of
    # upsert_given) hasn't round-tripped through the DB yet, so SQLAlchemy's Enum column
    # type hasn't coerced the plain str it was assigned into a SystemEnum member -- only a
    # record loaded via `select()` already holds a real enum instance.
    system = record.system
    return system.value if isinstance(system, SystemEnum) else system


def _state(record: UserConsentRecord) -> ConsentState:
    return ConsentState(
        id=record.id,
        user_id=record.user_id,
        external_user_id=record.external_user_id,
        system=_system_value(record),
        given_at=record.given_at,
        revoked_at=record.revoked_at,
        deletion_due_at=record.deletion_due_at,
        deleted_at=record.deleted_at,
        policy_version=record.policy_version,
    )


class SqlAlchemyConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_external(self, external_user_id: str, system: str) -> ConsentState | None:
        record = self._session.execute(
            select(UserConsentRecord).where(
                UserConsentRecord.external_user_id == external_user_id,
                UserConsentRecord.system == system,
            )
        ).scalar_one_or_none()
        return _state(record) if record else None

    def upsert_given(
        self,
        *,
        external_user_id: str,
        system: str,
        user_id: int | None,
        policy_version: str | None,
        now: datetime,
    ) -> ConsentState:
        record = self._session.execute(
            select(UserConsentRecord).where(
                UserConsentRecord.external_user_id == external_user_id,
                UserConsentRecord.system == system,
            )
        ).scalar_one_or_none()
        if record is None:
            record = UserConsentRecord(
                external_user_id=external_user_id,
                system=system,
                given_at=now,
                policy_version=policy_version,
            )
            self._session.add(record)
        else:
            # The caller (AcceptConsent) only reaches here when the current cycle is *not*
            # active -- never given, revoked, or a fully completed erasure cycle -- so this
            # is always a fresh cycle and `given_at` always gets today's date, never the
            # stale value from a prior cycle.
            record.given_at = now
            record.revoked_at = None
            record.deletion_due_at = None
            record.deleted_at = None
            record.policy_version = policy_version
        if user_id is not None:
            record.user_id = user_id
        self._session.flush()
        return _state(record)

    def set_revoked(
        self, consent_id: int, *, revoked_at: datetime, deletion_due_at: datetime
    ) -> ConsentState:
        record = self._session.get(UserConsentRecord, consent_id)
        if record is None:
            raise LookupError(consent_id)
        record.revoked_at = revoked_at
        record.deletion_due_at = deletion_due_at
        self._session.flush()
        return _state(record)

    def append_event(
        self,
        consent_id: int,
        event_type: ConsentEventType,
        *,
        occurred_at: datetime,
        policy_version: str | None,
    ) -> None:
        self._session.add(
            ConsentEventRecord(
                user_consent_id=consent_id,
                event_type=event_type,
                occurred_at=occurred_at,
                policy_version=policy_version,
            )
        )
        self._session.flush()

    def list_due_for_deletion(self, *, now: datetime) -> list[int]:
        rows = self._session.execute(
            select(UserConsentRecord.id).where(
                UserConsentRecord.revoked_at.is_not(None),
                UserConsentRecord.deleted_at.is_(None),
                UserConsentRecord.deletion_due_at.is_not(None),
                UserConsentRecord.deletion_due_at <= now,
            )
        ).scalars()
        return list(rows)
