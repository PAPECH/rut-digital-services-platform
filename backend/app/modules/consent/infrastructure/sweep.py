"""Retention sweep: hard-deletes an identity 10 business days after revoke (Task 064).

Runs on the same APScheduler worker as push_outbox / monitoring (see app.workers.run),
guarded by a Redis lock so multiple worker replicas don't double-process. Each due identity
is processed in its own session/transaction -- a failure on one must not affect the others,
and must not leave a half-deleted row (see docs/tasks/064, "no partial half-deleted state").
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.redis import redis_client
from ....db.session import SessionLocal
from ....models.attachment import Attachment
from ....services.files import delete_file
from ...profiles.infrastructure.models import User
from ..domain.entities import ConsentEventType
from .models import ConsentEventRecord, UserConsentRecord
from .repositories import SqlAlchemyConsentRepository

log = logging.getLogger(__name__)

LOCK_KEY = "mfc:consent_retention:lock"
LOCK_TTL = 300
# Hourly is ample resolution against a 10-business-day window; no reason to poll tighter.
INTERVAL_SECONDS = 3600


def tick() -> None:
    got = redis_client.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL)
    if not got:
        return
    try:
        run_sweep()
    finally:
        try:
            redis_client.delete(LOCK_KEY)
        except Exception as e:  # noqa: BLE001
            log.debug("consent retention lock release failed: %s", e)


def run_sweep() -> None:
    now = datetime.now(tz=UTC)
    with SessionLocal() as scan_db:
        due_ids = SqlAlchemyConsentRepository(scan_db).list_due_for_deletion(now=now)
    if not due_ids:
        return
    log.info("consent retention sweep: %s identity(ies) due", len(due_ids))
    for consent_id in due_ids:
        with SessionLocal() as db:
            try:
                _erase_one(db, consent_id, now=datetime.now(tz=UTC))
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
                log.exception("consent retention sweep failed for consent_id=%s", consent_id)


def _erase_one(db: Session, consent_id: int, *, now: datetime) -> None:
    record = db.execute(
        select(UserConsentRecord).where(UserConsentRecord.id == consent_id).with_for_update()
    ).scalar_one_or_none()
    if record is None:
        return
    # Defensive re-check: a re-consent could have landed between the scan and this row's turn.
    if record.deleted_at is not None or record.revoked_at is None:
        return
    if record.deletion_due_at is None or record.deletion_due_at > now:
        return

    user_id = record.user_id
    if user_id is not None:
        _erase_attachments(db, user_id)
        user = db.get(User, user_id)
        if user is not None:
            # Cascades at the database level to bot_memberships, messages, staff_favorites,
            # form_submissions (+ status history), push_outbox, user_actions,
            # monitoring_subscriptions, rating_subscriptions, admission_rating_subscriptions,
            # request_status_subscriptions -- every one of those FKs is ON DELETE CASCADE
            # (see docs/tasks/064, Data and migration impact).
            db.delete(user)
            db.flush()

    # Redundant with the DB's ON DELETE SET NULL on user_consents.user_id (which already
    # fired above), made explicit rather than relied on implicitly.
    record.user_id = None
    record.deleted_at = now
    db.add(
        ConsentEventRecord(
            user_consent_id=record.id,
            event_type=ConsentEventType.deletion_executed,
            occurred_at=now,
            policy_version=record.policy_version,
        )
    )
    db.flush()


def _erase_attachments(db: Session, user_id: int) -> None:
    """Attachment file bytes live behind the file-storage port, not in the row -- a DB
    constraint can't reach them, so this is explicit application-level cleanup rather than
    left to `attachments.uploaded_by_user_id`'s ON DELETE SET NULL."""
    attachments = list(
        db.execute(select(Attachment).where(Attachment.uploaded_by_user_id == user_id)).scalars()
    )
    for attachment in attachments:
        delete_file(attachment.storage_path)
        db.delete(attachment)
    if attachments:
        db.flush()


def schedule_jobs(scheduler) -> None:
    scheduler.add_job(
        tick,
        "interval",
        seconds=INTERVAL_SECONDS,
        id="consent_retention_sweep_tick",
        max_instances=1,
        coalesce=True,
    )
