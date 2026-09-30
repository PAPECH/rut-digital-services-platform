from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_admin
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..infrastructure.repository import SqlAlchemyAuditLogRepository
from .schemas import AuditEntryOut

router = APIRouter()


@router.get("", response_model=list[AuditEntryOut])
def list_audit_entries(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[AuditEntryOut]:
    entries = SqlAlchemyAuditLogRepository(db).list_for_bot(bot.id, limit=limit, offset=offset)
    return [AuditEntryOut.from_domain(entry) for entry in entries]
