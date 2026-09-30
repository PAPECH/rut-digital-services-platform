from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .....db.redis import redis_client
from .....db.session import SessionLocal
from ....admins.infrastructure.models import Admin
from ...infrastructure.models import CapabilityInstallationRecord
from ..application.ports import ScheduleHierarchyProvider, SyncEventBroadcaster
from ..application.use_cases import SyncGroupSchedule
from ..domain.entities import ManualSyncRequest, ScheduleGroup, ScheduleInstitute
from ..domain.manual_sync import validate_manual_sync_scope
from .oracle_provider import OracleTimetableProviderError
from .provider import MiitTimetableProviderError
from .provider_factory import get_schedule_provider
from .repositories import SqlAlchemyRutScheduleRepository
from .sync_log_repository import SqlAlchemyRutScheduleSyncLogRepository
from .sync_worker import LOCK_TTL_SECONDS, crawl_all_groups, lock_key, resolve_provider_error_code
from .tree_cache import RedisScheduleTreeCache

log = logging.getLogger(__name__)


class SyncAlreadyRunning(RuntimeError):
    pass


def _admin_name(db: Session, admin_id: int | None) -> str | None:
    if admin_id is None:
        return None
    return db.execute(select(Admin.full_name).where(Admin.id == admin_id)).scalar_one_or_none()


def _group_name(db: Session, group_external_id: str | None) -> str | None:
    if group_external_id is None:
        return None
    group = SqlAlchemyRutScheduleRepository(db).get_group(group_external_id)
    return group.name if group else None


def _institute_name(db: Session, institute_external_id: str | None) -> str | None:
    if institute_external_id is None:
        return None
    for institute in SqlAlchemyRutScheduleRepository(db).list_institutes():
        if institute.external_id == institute_external_id:
            return institute.name
    return None


def _enabled_rut_schedule_bot_ids(db: Session) -> list[int]:
    """Every bot with `rut_schedule` enabled -- the manual-sync log/live updates are platform-wide
    (see infrastructure/models.py), so a status change must reach every such bot's
    `platform_admin_room`, not just the one whose panel happened to trigger it. Otherwise a
    platform admin watching a *different* bot's panel would see a stale log until they manually
    refresh, even though the underlying data just changed for everyone."""
    return list(
        db.execute(
            select(CapabilityInstallationRecord.bot_instance_id).where(
                CapabilityInstallationRecord.capability_key == "rut_schedule",
                CapabilityInstallationRecord.is_enabled.is_(True),
            )
        ).scalars()
    )


async def _broadcast_to_all(db: Session, broadcaster: SyncEventBroadcaster, event: dict[str, Any]) -> None:
    for bot_instance_id in _enabled_rut_schedule_bot_ids(db):
        await broadcaster.broadcast(bot_instance_id, event)


def _event_payload(
    request: ManualSyncRequest,
    *,
    admin_name: str | None,
    group_name: str | None,
    institute_name: str | None,
) -> dict[str, Any]:
    return {
        "id": request.id,
        "requested_at": request.requested_at.isoformat(),
        "requested_by_admin_id": request.requested_by_admin_id,
        "requested_by_admin_name": admin_name,
        "provider": request.provider,
        "scope": request.scope,
        "group_external_id": request.group_external_id,
        "group_name": group_name,
        "institute_external_id": request.institute_external_id,
        "institute_name": institute_name,
        "status": request.status,
        "started_at": request.started_at.isoformat() if request.started_at else None,
        "finished_at": request.finished_at.isoformat() if request.finished_at else None,
        "groups_synced": request.groups_synced,
        "groups_failed": request.groups_failed,
        "error_code": request.error_code,
    }


async def enqueue_manual_sync(
    db: Session,
    broadcaster: SyncEventBroadcaster,
    *,
    bot_instance_id: int,
    installation_id: int,
    admin_id: int | None,
    provider_name: str,
    scope: str,
    group_external_id: str | None,
    institute_external_id: str | None = None,
) -> tuple[ManualSyncRequest, str | None, str | None, str | None]:
    """Synchronous (request-handling-time) half of a manual sync trigger (Task 045, extended with
    `scope="institute"` and platform-wide shared data as follow-ups): validates, acquires the one
    global Redis lock the nightly cron also uses (so a manual run and the cron -- or two manual
    runs from different bots' panels -- can never overlap), and creates the `queued` log row.
    `bot_instance_id`/`installation_id` are recorded on the row as context (which bot's panel
    triggered this) but no longer scope any read here -- the catalog/log are platform-wide. Raises
    `InvalidSyncRequest` (see domain/manual_sync.py) or `SyncAlreadyRunning`. On success, the lock
    is held by the caller -- the caller must schedule `run_manual_sync` (below) as a background
    task; it releases the lock when the crawl finishes."""
    repository = SqlAlchemyRutScheduleRepository(db)
    known_groups = {g.external_id for g in repository.list_all_groups()}
    known_institutes = {i.external_id for i in repository.list_institutes()}
    validate_manual_sync_scope(
        scope, group_external_id, institute_external_id, known_groups, known_institutes
    )

    key = lock_key()
    if not redis_client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS):
        raise SyncAlreadyRunning()

    try:
        sync_log = SqlAlchemyRutScheduleSyncLogRepository(db)
        request = sync_log.create(
            bot_instance_id=bot_instance_id,
            installation_id=installation_id,
            requested_by_admin_id=admin_id,
            provider=provider_name,
            scope=scope,
            group_external_id=group_external_id,
            institute_external_id=institute_external_id,
        )
    except Exception:
        redis_client.delete(key)
        raise

    admin_name = _admin_name(db, admin_id)
    group_name = _group_name(db, group_external_id)
    institute_name = _institute_name(db, institute_external_id)
    await _broadcast_to_all(
        db,
        broadcaster,
        _event_payload(request, admin_name=admin_name, group_name=group_name, institute_name=institute_name),
    )
    return request, admin_name, group_name, institute_name


async def run_manual_sync(
    broadcaster: SyncEventBroadcaster,
    *,
    request_id: int,
    scope: str,
    group_external_id: str | None,
    institute_external_id: str | None = None,
) -> None:
    """Background half of a manual sync trigger (Task 045). Runs inside the `backend` process
    itself (scheduled via FastAPI `BackgroundTasks`, not dispatched to the separate `worker`
    process) specifically so it shares a process with the admin WebSocket hub and can broadcast
    live status updates without new cross-process plumbing -- see Task 045's Architecture. Opens
    its own DB session and provider, exactly like the nightly worker's `sync_installation`, since a
    background task runs after the triggering HTTP request's own session has already been closed.
    No `bot_instance_id`/`installation_id` parameter: the crawl/reads and the broadcast fan-out
    (`_broadcast_to_all`) are platform-wide, see infrastructure/models.py."""
    provider: ScheduleHierarchyProvider = get_schedule_provider()
    try:
        with SessionLocal() as db:
            sync_log = SqlAlchemyRutScheduleSyncLogRepository(db)
            request = sync_log.mark_running(request_id, started_at=datetime.now(tz=UTC))
            db.commit()
            admin_name = _admin_name(db, request.requested_by_admin_id)
            group_name = _group_name(db, group_external_id)
            institute_name = _institute_name(db, institute_external_id)
            await _broadcast_to_all(
                db,
                broadcaster,
                _event_payload(
                    request, admin_name=admin_name, group_name=group_name, institute_name=institute_name
                ),
            )

            status = "succeeded"
            groups_synced: int | None = None
            groups_failed: int | None = None
            error_code: str | None = None
            try:
                if scope == "group":
                    assert group_external_id is not None
                    await SyncGroupSchedule(SqlAlchemyRutScheduleRepository(db), provider).execute(
                        group_external_id
                    )
                    db.commit()
                    groups_synced, groups_failed = 1, 0
                else:
                    if scope == "institute":
                        assert institute_external_id is not None
                        groups = SqlAlchemyRutScheduleRepository(db).list_groups_by_institute(
                            institute_external_id
                        )
                    else:
                        groups = SqlAlchemyRutScheduleRepository(db).list_all_groups()
                    groups_synced, groups_failed = await crawl_all_groups(db, provider, groups)
                    if groups_failed and groups_synced:
                        status = "partial"
                    elif groups_failed and not groups_synced:
                        status = "failed"
                        error_code = "sync_all_failed"
            except (
                MiitTimetableProviderError,
                OracleTimetableProviderError,
                NotImplementedError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                db.rollback()
                status = "failed"
                error_code = resolve_provider_error_code(exc)
                log.warning(
                    "rut-schedule manual sync failed for request %s (%s): %s",
                    request_id,
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )

            finished = sync_log.mark_finished(
                request_id,
                status=status,
                finished_at=datetime.now(tz=UTC),
                groups_synced=groups_synced,
                groups_failed=groups_failed,
                error_code=error_code,
            )
            db.commit()
            await _broadcast_to_all(
                db,
                broadcaster,
                _event_payload(
                    finished, admin_name=admin_name, group_name=group_name, institute_name=institute_name
                ),
            )
    finally:
        try:
            redis_client.delete(lock_key())
        except Exception as exc:
            log.debug("rut-schedule manual sync lock release failed: %s", type(exc).__name__)


async def refresh_groups(db: Session) -> tuple[int, int]:
    """"Обновить список групп" (Task 045 follow-up): a lightweight, synchronous refetch of just
    the institute/group catalog (one cheap request to `/timetable`) -- distinct from a manual
    lesson sync, so it does not create a `rut_schedule_manual_sync_requests` row or push a
    WebSocket event; it returns fast enough for the caller to just re-fetch `.../admin/groups`
    afterward. Still takes the same global Redis lock as a lesson sync, purely to avoid two live
    requests to the source site racing each other -- not because a concurrent catalog replace
    would corrupt an in-progress lesson crawl (that crawl already snapshotted its own group list
    before this could run). Raises `SyncAlreadyRunning` if the lock is held. Platform-wide, not
    per-bot (see infrastructure/models.py) -- the caller records which bot's panel triggered this
    in its own audit log, not here."""
    key = lock_key()
    if not redis_client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS):
        raise SyncAlreadyRunning()
    try:
        provider = get_schedule_provider()
        hierarchy = await provider.read_hierarchy()
        repository = SqlAlchemyRutScheduleRepository(db)
        repository.replace_hierarchy(
            [ScheduleInstitute(i.external_id, i.name) for i in hierarchy.institutes],
            [
                ScheduleGroup(g.external_id, g.name, g.institute_external_id, g.course_number)
                for g in hierarchy.groups
            ],
        )
        db.commit()
        # After commit, not before -- see sync_worker.py's sync_installation for why.
        RedisScheduleTreeCache().invalidate()
        return len(hierarchy.institutes), len(hierarchy.groups)
    finally:
        try:
            redis_client.delete(key)
        except Exception as exc:
            log.debug("rut-schedule refresh-groups lock release failed: %s", type(exc).__name__)
