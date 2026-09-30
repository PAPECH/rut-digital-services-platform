from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from .....db.redis import redis_client
from .....db.session import SessionLocal
from .....services.push import enqueue_push
from ...infrastructure.models import CapabilityInstallationRecord
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.ports import AdmissionRatingSnapshot, ProviderPlan
from ..application.use_cases import rating_change_notification_payload
from ..domain.change_policy import has_meaningful_rating_change
from ..domain.config import InvalidAdmissionRatingConfig, parse_admission_rating_config
from ..domain.identity import applicant_code_hash
from .models import (
    AdmissionRatingPlanRecord,
    AdmissionRatingStateRecord,
    AdmissionRatingSubscriptionRecord,
)
from .provider import RutAdmissionProvider, RutAdmissionProviderError, provider_error_code

log = logging.getLogger(__name__)

LOCK_TTL_SECONDS = 55 * 60
SCHEDULER_INTERVAL_SECONDS = 60


def lock_key(installation_id: int) -> str:
    return f"platform:capability:admission_rating:{installation_id}:sync"


def should_poll(last_health_at: datetime | None, interval: int, now: datetime) -> bool:
    if last_health_at is None:
        return True
    return (now - last_health_at).total_seconds() >= interval


def _save_plan(db, *, bot_id: int, installation_id: int, plan: ProviderPlan):
    record = db.execute(
        select(AdmissionRatingPlanRecord).where(
            AdmissionRatingPlanRecord.bot_instance_id == bot_id,
            AdmissionRatingPlanRecord.plan_id == plan.plan_id,
        )
    ).scalar_one_or_none()
    if record is None:
        record = AdmissionRatingPlanRecord(
            bot_instance_id=bot_id,
            installation_id=installation_id,
            plan_id=plan.plan_id,
            specialty=plan.specialty,
            qualification=plan.qualification,
        )
        db.add(record)
    else:
        record.installation_id = installation_id
        record.specialty = plan.specialty
        record.qualification = plan.qualification
    return record


def apply_snapshot(
    db,
    *,
    bot_id: int,
    installation_id: int,
    snapshot: AdmissionRatingSnapshot,
    checked_at: datetime,
) -> set[str]:
    plans = {plan.plan_id: plan for plan in snapshot.plans}
    for plan in plans.values():
        _save_plan(db, bot_id=bot_id, installation_id=installation_id, plan=plan)

    existing = {
        (state.plan_id, state.applicant_code_hash, state.competition): state
        for state in db.execute(
            select(AdmissionRatingStateRecord).where(
                AdmissionRatingStateRecord.bot_instance_id == bot_id,
                AdmissionRatingStateRecord.installation_id == installation_id,
            )
        ).scalars()
    }
    changed_hashes: set[str] = set()
    unique_ratings = {
        (rating.plan_id, rating.applicant_code, rating.competition): rating for rating in snapshot.ratings
    }
    for rating in unique_ratings.values():
        plan = plans.get(rating.plan_id)
        if plan is None:
            continue
        code_hash = applicant_code_hash(bot_id, rating.applicant_code)
        key = (rating.plan_id, code_hash, rating.competition)
        current = existing.get(key)
        total = max(0, int(plan.totals.get(rating.competition, 0)))
        if current is None:
            current = AdmissionRatingStateRecord(
                bot_instance_id=bot_id,
                installation_id=installation_id,
                plan_id=rating.plan_id,
                applicant_code=rating.applicant_code,
                applicant_code_hash=code_hash,
                points=rating.points,
                preference=rating.preference,
                competition=rating.competition,
                group_name=rating.group_name,
                position=rating.position,
                total=total,
                checked_at=checked_at,
            )
            db.add(current)
            existing[key] = current
            continue
        if has_meaningful_rating_change(
            old_position=current.position,
            new_position=rating.position,
            old_group=current.group_name,
            new_group=rating.group_name,
            available_places=total,
        ):
            changed_hashes.add(code_hash)
        current.applicant_code = rating.applicant_code
        current.points = rating.points
        current.preference = rating.preference
        current.group_name = rating.group_name
        current.position = rating.position
        current.total = total
        current.checked_at = checked_at
    db.flush()
    return changed_hashes


def _enqueue_notifications(
    db,
    *,
    bot_id: int,
    installation_id: int,
    changed_hashes: set[str],
) -> int:
    if not changed_hashes:
        return 0
    subscriptions = db.execute(
        select(AdmissionRatingSubscriptionRecord).where(
            AdmissionRatingSubscriptionRecord.bot_instance_id == bot_id,
            AdmissionRatingSubscriptionRecord.installation_id == installation_id,
            AdmissionRatingSubscriptionRecord.applicant_code_hash.in_(changed_hashes),
            AdmissionRatingSubscriptionRecord.is_active.is_(True),
        )
    ).scalars()
    count = 0
    for subscription in subscriptions:
        enqueue_push(
            db,
            bot_instance_id=bot_id,
            user_id=subscription.user_id,
            kind="admission_rating_changed",
            payload=rating_change_notification_payload(installation_id),
        )
        count += 1
    return count


async def sync_installation(installation_id: int) -> None:

    key = lock_key(installation_id)
    if not redis_client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS):
        return
    try:
        with SessionLocal() as db:
            record = db.execute(
                select(CapabilityInstallationRecord).where(
                    CapabilityInstallationRecord.id == installation_id,
                    CapabilityInstallationRecord.capability_key == "admission_rating",
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalar_one_or_none()

            if record is None:
                return
            now = datetime.now(tz=UTC)
            try:
                config = parse_admission_rating_config(record.config)

                if not should_poll(record.last_health_at, config.polling_interval_seconds, now):
                    return

                snapshot = await RutAdmissionProvider().read_snapshot(config)
                changed_hashes = apply_snapshot(
                    db,
                    bot_id=record.bot_instance_id,
                    installation_id=record.id,
                    snapshot=snapshot,
                    checked_at=now,
                )
                notification_count = 0
                if config.notifications_enabled:
                    notification_count = _enqueue_notifications(
                        db,
                        bot_id=record.bot_instance_id,
                        installation_id=record.id,
                        changed_hashes=changed_hashes,
                    )
                repository = SqlAlchemyCapabilityInstallationRepository(db)
                installation = repository.get(record.bot_instance_id, "admission_rating")
                assert installation is not None
                repository.save(
                    replace(
                        installation,
                        last_health_status="healthy",
                        last_health_at=now,
                        last_health_error_code=None,
                    )
                )
                db.commit()

                log.info(
                    "admission-rating sync completed for installation %s: %s plan(s), "
                    "%s rating row(s), %s notification(s)",
                    installation_id,
                    len(snapshot.plans),
                    len(snapshot.ratings),
                    notification_count,
                )
            except (
                InvalidAdmissionRatingConfig,
                RutAdmissionProviderError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                db.rollback()
                current = db.execute(
                    select(CapabilityInstallationRecord).where(
                        CapabilityInstallationRecord.id == installation_id,
                        CapabilityInstallationRecord.bot_instance_id == record.bot_instance_id,
                    )
                ).scalar_one_or_none()
                if current is not None:
                    current.last_health_status = "degraded"
                    current.last_health_at = now
                    current.last_health_error_code = (
                        "config_invalid"
                        if isinstance(exc, InvalidAdmissionRatingConfig)
                        else provider_error_code(exc)
                    )
                    db.commit()
                log.warning(
                    "admission-rating sync failed for installation %s (%s): %s",
                        installation_id,
                        type(exc).__name__,
                        exc,
                        exc_info=True,
                )
    finally:
        try:
            redis_client.delete(key)
        except Exception as exc:
            log.debug("admission-rating lock release failed: %s", type(exc).__name__)


async def tick() -> None:
    with SessionLocal() as db:
        installation_ids = list(
            db.execute(
                select(CapabilityInstallationRecord.id).where(
                    CapabilityInstallationRecord.capability_key == "admission_rating",
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalars()
        )
    for installation_id in installation_ids:

        await sync_installation(installation_id)


def tick_sync() -> None:
    asyncio.run(tick())


def schedule_jobs(scheduler) -> None:

    scheduler.add_job(
        tick_sync,
        "interval",
        seconds=SCHEDULER_INTERVAL_SECONDS,
        id="admission_rating_capability_tick",
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(tz=UTC),
    )
