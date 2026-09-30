from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from .....api.deps import CurrentPrincipal, require_platform_admin
from .....core.errors import conflict, not_found, service_unavailable, unprocessable
from .....db.session import get_db
from .....services.rate_limit import rate_limit
from ....audit.infrastructure.models import AuditLog
from ....bot_instances.domain.entities import BotInstance
from ....tenancy.presentation.dependencies import require_tenant_access
from ...application.use_cases import CapabilityDisabled, CapabilityNotInstalled, GetEnabledCapability
from ...domain.entities import CapabilityInstallation, UnknownCapability
from ...infrastructure.catalog import capability_registry
from ...infrastructure.repositories import SqlAlchemyCapabilityInstallationRepository
from ..domain.config import InvalidRutScheduleConfig, RutScheduleConfig, parse_rut_schedule_config
from ..domain.entities import ManualSyncRequest
from ..domain.manual_sync import InvalidSyncRequest
from ..infrastructure.manual_sync import (
    SyncAlreadyRunning,
    enqueue_manual_sync,
    refresh_groups,
    run_manual_sync,
)
from ..infrastructure.oracle_provider import OracleTimetableProviderError
from ..infrastructure.provider import MiitTimetableProviderError
from ..infrastructure.repositories import SqlAlchemyRutScheduleRepository
from ..infrastructure.sync_log_repository import SqlAlchemyRutScheduleSyncLogRepository
from ..infrastructure.sync_worker import resolve_provider_error_code
from ..infrastructure.ws_broadcaster import WsHubSyncEventBroadcaster
from .schemas import (
    GroupResponse,
    GroupWithLastSyncResponse,
    InstituteResponse,
    ManualSyncRequestResponse,
    ManualSyncTriggerRequest,
    RefreshGroupsResponse,
)

router = APIRouter()
_sync_trigger_limit = rate_limit("capability_rut_schedule_manual_sync", limit=10, window_seconds=60)


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _enabled(db: Session, bot_id: int) -> tuple[CapabilityInstallation, RutScheduleConfig]:
    try:
        installation, _ = GetEnabledCapability(
            SqlAlchemyCapabilityInstallationRepository(db), capability_registry
        ).execute(bot_id, "rut_schedule")
        assert installation.id is not None
        return installation, parse_rut_schedule_config(installation.config)
    except (
        CapabilityNotInstalled,
        CapabilityDisabled,
        UnknownCapability,
        InvalidRutScheduleConfig,
    ) as exc:
        raise not_found("Capability is unavailable", code="capability_disabled") from exc


def _sync_request_response(
    request: ManualSyncRequest,
    *,
    admin_name: str | None,
    group_name: str | None,
    institute_name: str | None,
) -> ManualSyncRequestResponse:
    assert request.id is not None
    return ManualSyncRequestResponse(
        id=request.id,
        requested_at=request.requested_at.isoformat(),
        requested_by_admin_id=request.requested_by_admin_id,
        requested_by_admin_name=admin_name,
        provider=request.provider,
        scope=request.scope,
        group_external_id=request.group_external_id,
        group_name=group_name,
        institute_external_id=request.institute_external_id,
        institute_name=institute_name,
        status=request.status,
        started_at=request.started_at.isoformat() if request.started_at else None,
        finished_at=request.finished_at.isoformat() if request.finished_at else None,
        groups_synced=request.groups_synced,
        groups_failed=request.groups_failed,
        error_code=request.error_code,
    )


def _audit_manual_sync(
    db: Session,
    *,
    admin_id: int | None,
    bot_id: int,
    installation_id: int,
    scope: str,
    group_external_id: str | None,
    institute_external_id: str | None,
) -> None:
    # Same shape/convention as `capabilities/presentation/router.py`'s `_audit()` -- the permanent
    # cross-feature audit trail, independent of the dedicated sync-requests log/WebSocket updates
    # above (see Task 045's API contracts section).
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_id,
            method="CAPABILITY",
            path="/api/capabilities/rut-schedule/admin/sync",
            status_code=200,
            meta={
                "action": "rut_schedule_manual_sync_requested",
                "bot_instance_id": bot_id,
                "installation_id": installation_id,
                "scope": scope,
                "group_external_id": group_external_id,
                "institute_external_id": institute_external_id,
            },
        )
    )


def _audit_refresh_groups(
    db: Session, *, admin_id: int | None, bot_id: int, installation_id: int
) -> None:
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_id,
            method="CAPABILITY",
            path="/api/capabilities/rut-schedule/admin/refresh-groups",
            status_code=200,
            meta={
                "action": "rut_schedule_groups_refreshed",
                "bot_instance_id": bot_id,
                "installation_id": installation_id,
            },
        )
    )


@router.post(
    "/sync",
    response_model=ManualSyncRequestResponse,
    dependencies=[Depends(_sync_trigger_limit)],
)
async def trigger_manual_sync(
    payload: ManualSyncTriggerRequest,
    background_tasks: BackgroundTasks,
    principal: CurrentPrincipal = Depends(require_platform_admin),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> ManualSyncRequestResponse:
    bot_id = _bot_id(bot)
    installation, config = _enabled(db, bot_id)
    assert installation.id is not None
    try:
        request, admin_name, group_name, institute_name = await enqueue_manual_sync(
            db,
            WsHubSyncEventBroadcaster(),
            bot_instance_id=bot_id,
            installation_id=installation.id,
            admin_id=principal.admin_id,
            provider_name=config.provider,
            scope=payload.scope,
            group_external_id=payload.group_external_id,
            institute_external_id=payload.institute_external_id,
        )
        _audit_manual_sync(
            db,
            admin_id=principal.admin_id,
            bot_id=bot_id,
            installation_id=installation.id,
            scope=payload.scope,
            group_external_id=payload.group_external_id,
            institute_external_id=payload.institute_external_id,
        )
        db.commit()
    except InvalidSyncRequest as exc:
        db.rollback()
        raise unprocessable(str(exc), code="sync_request_invalid", path=exc.path) from exc
    except SyncAlreadyRunning as exc:
        db.rollback()
        raise conflict(
            "A sync is already running for this installation", code="sync_already_running"
        ) from exc

    background_tasks.add_task(
        run_manual_sync,
        WsHubSyncEventBroadcaster(),
        request_id=request.id,
        scope=payload.scope,
        group_external_id=payload.group_external_id,
        institute_external_id=payload.institute_external_id,
    )
    return _sync_request_response(
        request, admin_name=admin_name, group_name=group_name, institute_name=institute_name
    )


@router.get("/sync-requests", response_model=list[ManualSyncRequestResponse])
def list_sync_requests(
    limit: int = Query(default=50, ge=1, le=200),
    _: CurrentPrincipal = Depends(require_platform_admin),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[ManualSyncRequestResponse]:
    bot_id = _bot_id(bot)
    _installation, _config = _enabled(db, bot_id)
    rows = SqlAlchemyRutScheduleSyncLogRepository(db).list_recent(limit)
    return [
        _sync_request_response(
            request, admin_name=admin_name, group_name=group_name, institute_name=institute_name
        )
        for request, admin_name, group_name, institute_name in rows
    ]


@router.post(
    "/refresh-groups",
    response_model=RefreshGroupsResponse,
    dependencies=[Depends(_sync_trigger_limit)],
)
async def refresh_groups_endpoint(
    principal: CurrentPrincipal = Depends(require_platform_admin),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> RefreshGroupsResponse:
    bot_id = _bot_id(bot)
    installation, _config = _enabled(db, bot_id)
    assert installation.id is not None
    try:
        institutes_count, groups_count = await refresh_groups(db)
        _audit_refresh_groups(
            db, admin_id=principal.admin_id, bot_id=bot_id, installation_id=installation.id
        )
        db.commit()
    except SyncAlreadyRunning as exc:
        db.rollback()
        raise conflict(
            "A sync is already running for this installation", code="sync_already_running"
        ) from exc
    except (
        MiitTimetableProviderError,
        OracleTimetableProviderError,
        NotImplementedError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        db.rollback()
        raise service_unavailable(
            "Не удалось обновить список групп", code=resolve_provider_error_code(exc)
        ) from exc
    return RefreshGroupsResponse(institutes_count=institutes_count, groups_count=groups_count)


@router.get("/institutes", response_model=list[InstituteResponse])
def list_institutes_admin(
    _: CurrentPrincipal = Depends(require_platform_admin),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[InstituteResponse]:
    # Same data the student-facing /institutes endpoint serves, just platform-admin-gated -- the
    # checkbox tree (Task 045 follow-up) needs display names, not just institute codes.
    bot_id = _bot_id(bot)
    _installation, _config = _enabled(db, bot_id)
    result = SqlAlchemyRutScheduleRepository(db).list_institutes()
    return [InstituteResponse(external_id=item.external_id, name=item.name) for item in result]


@router.get("/groups", response_model=list[GroupWithLastSyncResponse])
def list_groups_with_last_sync(
    # Ceiling comfortably above a real directory's current size (~704 groups, see Task 043's
    # verification notes) so the admin panel's table/trigger picker can fetch everything in one
    # page without a pagination UI, while the endpoint still accepts `limit`/`offset` for a future
    # one if a directory ever outgrows this.
    limit: int = Query(default=1000, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    _: CurrentPrincipal = Depends(require_platform_admin),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[GroupWithLastSyncResponse]:
    bot_id = _bot_id(bot)
    _installation, _config = _enabled(db, bot_id)
    rows = SqlAlchemyRutScheduleRepository(db).list_groups_with_last_sync(limit=limit, offset=offset)
    return [
        GroupWithLastSyncResponse(
            group=GroupResponse(
                external_id=item.group.external_id,
                name=item.group.name,
                institute_external_id=item.group.institute_external_id,
                course_number=item.group.course_number,
            ),
            last_synced_at=item.last_synced_at.isoformat() if item.last_synced_at else None,
        )
        for item in rows
    ]
