from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .....db.redis import redis_client
from .....db.session import SessionLocal
from ...infrastructure.models import CapabilityInstallationRecord
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..application.ports import ScheduleHierarchyProvider
from ..application.use_cases import SyncGroupSchedule
from ..domain.config import InvalidRutScheduleConfig, parse_rut_schedule_config
from ..domain.entities import ScheduleGroup, ScheduleInstitute
from .oracle_provider import OracleTimetableProviderError
from .oracle_provider import provider_error_code as _oracle_provider_error_code
from .provider import MiitTimetableProviderError
from .provider import provider_error_code as _miit_provider_error_code
from .provider_factory import get_schedule_provider
from .repositories import SqlAlchemyRutScheduleRepository
from .tree_cache import RedisScheduleTreeCache

log = logging.getLogger(__name__)

# One nightly run now crawls the hierarchy plus every group's lessons (hundreds of requests, see
# `sync_installation` below), not just the cheap hierarchy page -- sized with headroom over a
# realistic worst-case run, not the few seconds a hierarchy-only sync used to need.
LOCK_TTL_SECONDS = 90 * 60
# Delay between each group's lesson fetch during the nightly crawl -- polite pacing against a
# site this platform doesn't control, even during its one permitted nightly window.
GROUP_SYNC_DELAY_SECONDS = 0.4
# The source site must only ever be hit once a night, never during the day (an operational
# constraint on miit.ru itself, not a preference) -- a fixed cron time, not an interval timer, so
# a worker container restart during the day can never trigger an extra daytime run. 23:00 UTC ==
# 02:00 Moscow time.
NIGHTLY_SYNC_HOUR_UTC = 23
NIGHTLY_SYNC_MINUTE_UTC = 0

# Platform-wide, not per-installation: the miit.ru catalog/lessons are shared by every bot that
# enables rut_schedule (see infrastructure/models.py's module docstring and Task 045's "Follow-up,
# 2026-09-02"), so at most one crawl -- triggered by whichever enabled installation's tick gets to
# it first -- may run at a time, regardless of how many bots have the capability enabled.
_LOCK_KEY = "platform:capability:rut_schedule:global:hierarchy_sync"


def lock_key() -> str:
    return _LOCK_KEY


def resolve_provider_error_code(exc: Exception) -> str:
    if isinstance(exc, OracleTimetableProviderError):
        return _oracle_provider_error_code(exc)
    if isinstance(exc, NotImplementedError):
        return "provider_not_implemented"
    return _miit_provider_error_code(exc)


def should_poll(last_synced_at: datetime | None, interval: int, now: datetime) -> bool:
    if last_synced_at is None:
        return True
    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=UTC)
    return (now - last_synced_at).total_seconds() >= interval


async def crawl_all_groups(
    db: Session,
    provider: ScheduleHierarchyProvider,
    groups: Iterable[ScheduleGroup],
) -> tuple[int, int]:
    """Fetches every given group's lessons and persists them via the same `SyncGroupSchedule` use
    case the nightly crawl always used -- shared by the nightly tick (below) and the platform-admin
    manual "run all groups"/"run institute" triggers (Task 045), so there's exactly one place that
    does this, not a second copy. A single group's failure is logged and skipped, not allowed to
    abort the rest. Returns (synced, failed) counts."""
    synced, failed = 0, 0
    for group in groups:
        await asyncio.sleep(GROUP_SYNC_DELAY_SECONDS)
        try:
            await SyncGroupSchedule(SqlAlchemyRutScheduleRepository(db), provider).execute(
                group.external_id
            )
            db.commit()
            synced += 1
        except (
            MiitTimetableProviderError,
            OracleTimetableProviderError,
            NotImplementedError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            db.rollback()
            failed += 1
            log.warning(
                "rut-schedule group lesson sync failed for group %s (%s): %s",
                group.external_id,
                type(exc).__name__,
                exc,
            )
    return synced, failed


async def sync_installation(installation_id: int) -> None:
    """Despite the name/param (kept for continuity with `tick()`'s per-installation loop and each
    installation's own config/health tracking), the crawl this triggers writes to the platform-wide
    catalog, not anything scoped to `installation_id` -- see infrastructure/models.py. Whichever
    enabled installation's tick is first to find the shared data due for a refresh does the one
    crawl for the night; every other installation's tick will find the global lock held (or the
    data already fresh) and skip without hitting the site again."""
    with SessionLocal() as db:
        record = db.execute(
            select(CapabilityInstallationRecord).where(
                CapabilityInstallationRecord.id == installation_id,
                CapabilityInstallationRecord.capability_key == "rut_schedule",
                CapabilityInstallationRecord.is_enabled.is_(True),
            )
        ).scalar_one_or_none()
        if record is None:
            return
        bot_instance_id = record.bot_instance_id
        now = datetime.now(tz=UTC)
        try:
            config = parse_rut_schedule_config(record.config)
        except InvalidRutScheduleConfig:
            return
        if not config.night_auto_sync_enabled:
            return
        repository = SqlAlchemyRutScheduleRepository(db)
        last_synced_at = repository.hierarchy_last_synced_at()
        if not should_poll(last_synced_at, config.hierarchy_sync_interval_seconds, now):
            return

    key = lock_key()
    if not redis_client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS):
        return
    try:
        with SessionLocal() as db:
            provider = get_schedule_provider()
            repository = SqlAlchemyRutScheduleRepository(db)
            try:
                hierarchy = await provider.read_hierarchy()
                repository.replace_hierarchy(
                    [ScheduleInstitute(i.external_id, i.name) for i in hierarchy.institutes],
                    [
                        ScheduleGroup(g.external_id, g.name, g.institute_external_id, g.course_number)
                        for g in hierarchy.groups
                    ],
                )
                installation_repo = SqlAlchemyCapabilityInstallationRepository(db)
                installation = installation_repo.get(bot_instance_id, "rut_schedule")
                assert installation is not None
                installation_repo.save(
                    replace(
                        installation,
                        last_health_status="healthy",
                        last_health_at=now,
                        last_health_error_code=None,
                    )
                )
                db.commit()
                # After commit, not before: invalidating first would let a concurrent reader
                # rebuild-and-cache the still-old (pre-commit) data in the window between the two.
                RedisScheduleTreeCache().invalidate()
                log.info(
                    "rut-schedule hierarchy sync completed (platform-wide): "
                    "%s institute(s), %s group(s)",
                    len(hierarchy.institutes),
                    len(hierarchy.groups),
                )
            except (
                MiitTimetableProviderError,
                OracleTimetableProviderError,
                NotImplementedError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                db.rollback()
                current = db.execute(
                    select(CapabilityInstallationRecord).where(
                        CapabilityInstallationRecord.id == installation_id,
                    )
                ).scalar_one_or_none()
                if current is not None:
                    current.last_health_status = "degraded"
                    current.last_health_at = now
                    current.last_health_error_code = resolve_provider_error_code(exc)
                    db.commit()
                log.warning(
                    "rut-schedule hierarchy sync failed (platform-wide) (%s): %s",
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                return

            # Hierarchy synced -- now eagerly crawl every group's lessons in the same nightly
            # window, so GetGroupSchedule (the user-facing read) never has to fetch live: a
            # single group's failure here is logged and skipped, not allowed to abort the whole
            # night's crawl or flip the installation's health status (that already reflects
            # whether the hierarchy sync itself succeeded).
            synced, failed = await crawl_all_groups(db, provider, hierarchy.groups)
            log.info(
                "rut-schedule group lesson crawl finished (platform-wide): %s synced, %s failed",
                synced,
                failed,
            )
    finally:
        try:
            redis_client.delete(key)
        except Exception as exc:
            log.debug("rut-schedule lock release failed: %s", type(exc).__name__)


async def tick() -> None:
    with SessionLocal() as db:
        installation_ids = list(
            db.execute(
                select(CapabilityInstallationRecord.id).where(
                    CapabilityInstallationRecord.capability_key == "rut_schedule",
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalars()
        )
    for installation_id in installation_ids:
        await sync_installation(installation_id)


def tick_sync() -> None:
    asyncio.run(tick())


def schedule_jobs(scheduler) -> None:
    # No `next_run_time` override here on purpose: a cron trigger with none set only ever fires
    # at its next real occurrence of 23:00 UTC, never immediately on job registration -- so
    # starting or restarting the worker container during the day cannot trigger a same-day run.
    scheduler.add_job(
        tick_sync,
        "cron",
        hour=NIGHTLY_SYNC_HOUR_UTC,
        minute=NIGHTLY_SYNC_MINUTE_UTC,
        id="rut_schedule_capability_hierarchy_tick",
        max_instances=1,
        coalesce=True,
    )
