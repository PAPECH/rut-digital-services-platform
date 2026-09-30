from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...admins.infrastructure.models import Admin
from ..domain.entities import AuditEntry
from .models import AuditLog


class SqlAlchemyAuditLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_bot(self, bot_instance_id: int, *, limit: int, offset: int) -> list[AuditEntry]:
        rows = self._db.execute(
            select(AuditLog, Admin.full_name)
            .outerjoin(Admin, Admin.id == AuditLog.admin_id)
            .where(AuditLog.bot_instance_id == bot_instance_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return [
            AuditEntry(
                id=entry.id,
                created_at=entry.created_at,
                admin_id=entry.admin_id,
                admin_name=admin_name,
                method=entry.method,
                path=entry.path,
                status_code=entry.status_code,
                duration_ms=entry.duration_ms,
                meta=entry.meta,
            )
            for entry, admin_name in rows
        ]
