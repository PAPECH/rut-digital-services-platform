"""Poll enabled request-status capability installations per tenant."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from ..db.redis import redis_client
from ..db.session import SessionLocal
from ..modules.capabilities.infrastructure.models import CapabilityInstallationRecord
from ..modules.capabilities.infrastructure.repositories import (
    SqlAlchemyCapabilityInstallationRepository,
)
from ..modules.capabilities.request_status.domain.config import (
    InvalidRequestStatusConfig,
    parse_request_status_config,
)
from ..modules.capabilities.request_status.domain.entities import RequestStatusState
from ..modules.capabilities.request_status.domain.identity import request_number_hash
from ..modules.capabilities.request_status.infrastructure.models import (
    RequestStatusStateRecord,
    RequestStatusSubscriptionRecord,
)
from ..modules.capabilities.request_status.infrastructure.provider import (
    GoogleSheetsStatusProvider,
    provider_error_code,
)
from ..modules.capabilities.request_status.infrastructure.repositories import (
    SqlAlchemyRequestStatusRepository,
)
from ..services.push import enqueue_push

log = logging.getLogger(__name__)

LOCK_TTL = 55
SCHEDULER_INTERVAL_SECONDS = 60


def _lock_key(installation_id: int) -> str:
    return f"platform:capability:request_status:{installation_id}:sync"


def _should_poll(installation: CapabilityInstallationRecord, interval: int, now: datetime) -> bool:
    if installation.last_health_at is None:
        return True
    return (now - installation.last_health_at).total_seconds() >= interval


def _sync_installation(installation_id: int) -> None:
    lock_key = _lock_key(installation_id)
    if not redis_client.set(lock_key, "1", nx=True, ex=LOCK_TTL):
        return
    try:
        with SessionLocal() as db:
            record = db.execute(
                select(CapabilityInstallationRecord).where(
                    CapabilityInstallationRecord.id == installation_id,
                    CapabilityInstallationRecord.capability_key == "request_status",
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalar_one_or_none()
            if record is None:
                return
            now = datetime.now(tz=UTC)
            try:
                config = parse_request_status_config(record.config)
                if not _should_poll(record, config.polling_interval_seconds, now):
                    return
                statuses = GoogleSheetsStatusProvider(
                    circuit_key=f"{record.bot_instance_id}:{record.id}"
                ).read_statuses(config)
            except (InvalidRequestStatusConfig, OSError, ValueError, RuntimeError) as exc:
                record.last_health_status = "degraded"
                record.last_health_at = now
                record.last_health_error_code = (
                    "config_invalid"
                    if isinstance(exc, InvalidRequestStatusConfig)
                    else provider_error_code(exc)
                )
                db.commit()
                log.warning(
                    "request-status sync failed for installation %s",
                    installation_id,
                )
                return

            existing = {
                state.request_number_hash: state
                for state in db.execute(
                    select(RequestStatusStateRecord).where(
                        RequestStatusStateRecord.bot_instance_id == record.bot_instance_id,
                        RequestStatusStateRecord.installation_id == record.id,
                    )
                ).scalars()
            }
            states: list[RequestStatusState] = []
            changed_hashes: set[str] = set()
            for request_number, status in statuses.items():
                number_hash = request_number_hash(record.bot_instance_id, request_number)
                previous = existing.get(number_hash)
                if previous is not None and previous.last_status != status:
                    changed_hashes.add(number_hash)
                states.append(
                    RequestStatusState(
                        id=previous.id if previous else None,
                        bot_instance_id=record.bot_instance_id,
                        installation_id=record.id,
                        request_number=request_number,
                        request_number_hash=number_hash,
                        last_status=status,
                        checked_at=now,
                        source_revision=previous.source_revision if previous else 0,
                    )
                )
            SqlAlchemyRequestStatusRepository(db).upsert_states(states)

            if config.notifications_enabled and changed_hashes:
                subscriptions = db.execute(
                    select(RequestStatusSubscriptionRecord).where(
                        RequestStatusSubscriptionRecord.bot_instance_id == record.bot_instance_id,
                        RequestStatusSubscriptionRecord.installation_id == record.id,
                        RequestStatusSubscriptionRecord.request_number_hash.in_(changed_hashes),
                        RequestStatusSubscriptionRecord.is_active.is_(True),
                    )
                ).scalars()
                for subscription in subscriptions:
                    enqueue_push(
                        db,
                        bot_instance_id=record.bot_instance_id,
                        user_id=subscription.user_id,
                        kind="request_status_changed",
                        payload={"installation_id": record.id},
                    )

            repository = SqlAlchemyCapabilityInstallationRepository(db)
            domain_installation = repository.get(record.bot_instance_id, "request_status")
            assert domain_installation is not None
            repository.save(
                replace(
                    domain_installation,
                    last_health_status="healthy",
                    last_health_at=now,
                    last_health_error_code=None,
                )
            )
            db.commit()
            log.info(
                "request-status sync completed for installation %s: %s row(s), %s change(s)",
                installation_id,
                len(states),
                len(changed_hashes),
            )
    finally:
        try:
            redis_client.delete(lock_key)
        except Exception as exc:
            log.debug("request-status lock release failed: %s", type(exc).__name__)


def tick() -> None:
    with SessionLocal() as db:
        installation_ids = list(
            db.execute(
                select(CapabilityInstallationRecord.id).where(
                    CapabilityInstallationRecord.capability_key == "request_status",
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalars()
        )
    for installation_id in installation_ids:
        _sync_installation(installation_id)


def schedule_jobs(scheduler) -> None:
    scheduler.add_job(
        tick,
        "interval",
        seconds=SCHEDULER_INTERVAL_SECONDS,
        id="request_status_capability_tick",
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(tz=UTC),
    )
