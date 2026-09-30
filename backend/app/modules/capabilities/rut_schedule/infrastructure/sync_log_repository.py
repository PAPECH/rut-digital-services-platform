from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....admins.infrastructure.models import Admin
from ..domain.entities import ManualSyncRequest
from .models import (
    RutScheduleGroupRecord,
    RutScheduleInstituteRecord,
    RutScheduleManualSyncRequestRecord,
)


def _entity(row: RutScheduleManualSyncRequestRecord) -> ManualSyncRequest:
    return ManualSyncRequest(
        id=row.id,
        bot_instance_id=row.bot_instance_id,
        installation_id=row.installation_id,
        requested_by_admin_id=row.requested_by_admin_id,
        requested_at=row.requested_at,
        provider=row.provider,
        scope=row.scope,
        group_external_id=row.group_external_id,
        institute_external_id=row.institute_external_id,
        status=row.status,
        started_at=row.started_at,
        finished_at=row.finished_at,
        groups_synced=row.groups_synced,
        groups_failed=row.groups_failed,
        error_code=row.error_code,
    )


class SqlAlchemyRutScheduleSyncLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        bot_instance_id: int,
        installation_id: int,
        requested_by_admin_id: int | None,
        provider: str,
        scope: str,
        group_external_id: str | None,
        institute_external_id: str | None = None,
    ) -> ManualSyncRequest:
        row = RutScheduleManualSyncRequestRecord(
            bot_instance_id=bot_instance_id,
            installation_id=installation_id,
            requested_by_admin_id=requested_by_admin_id,
            requested_at=datetime.now(tz=UTC),
            provider=provider,
            scope=scope,
            group_external_id=group_external_id,
            institute_external_id=institute_external_id,
            status="queued",
        )
        self._session.add(row)
        self._session.flush()
        return _entity(row)

    def mark_running(self, request_id: int, *, started_at: datetime) -> ManualSyncRequest:
        row = self._session.get(RutScheduleManualSyncRequestRecord, request_id)
        assert row is not None
        row.status = "running"
        row.started_at = started_at
        self._session.flush()
        return _entity(row)

    def mark_finished(
        self,
        request_id: int,
        *,
        status: str,
        finished_at: datetime,
        groups_synced: int | None = None,
        groups_failed: int | None = None,
        error_code: str | None = None,
    ) -> ManualSyncRequest:
        row = self._session.get(RutScheduleManualSyncRequestRecord, request_id)
        assert row is not None
        row.status = status
        row.finished_at = finished_at
        row.groups_synced = groups_synced
        row.groups_failed = groups_failed
        row.error_code = error_code
        self._session.flush()
        return _entity(row)

    def list_recent(
        self, limit: int
    ) -> list[tuple[ManualSyncRequest, str | None, str | None, str | None]]:
        rows = self._session.execute(
            select(
                RutScheduleManualSyncRequestRecord,
                Admin.full_name,
                RutScheduleGroupRecord.name,
                RutScheduleInstituteRecord.name,
            )
            .outerjoin(Admin, Admin.id == RutScheduleManualSyncRequestRecord.requested_by_admin_id)
            .outerjoin(
                RutScheduleGroupRecord,
                RutScheduleGroupRecord.external_id == RutScheduleManualSyncRequestRecord.group_external_id,
            )
            .outerjoin(
                RutScheduleInstituteRecord,
                RutScheduleInstituteRecord.external_id
                == RutScheduleManualSyncRequestRecord.institute_external_id,
            )
            .order_by(
                RutScheduleManualSyncRequestRecord.requested_at.desc(),
                RutScheduleManualSyncRequestRecord.id.desc(),
            )
            .limit(limit)
        ).all()
        return [
            (_entity(row), admin_name, group_name, institute_name)
            for row, admin_name, group_name, institute_name in rows
        ]
