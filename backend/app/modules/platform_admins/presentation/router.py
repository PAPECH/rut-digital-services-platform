from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin
from ....core.errors import bad_request
from ....db.session import get_db
from ...audit.infrastructure.models import AuditLog
from ..application.commands import EnsurePlatformAdminCommand
from ..application.use_cases import EnsurePlatformAdmin, ListPlatformAdmins
from ..infrastructure.repository import SqlAlchemyPlatformAdminRepository
from .schemas import (
    EnsurePlatformAdminRequest,
    EnsurePlatformAdminResponse,
    PlatformAdminResponse,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
PlatformPrincipal = Annotated[CurrentPrincipal, Depends(require_platform_admin)]


@router.get("", response_model=list[PlatformAdminResponse])
def list_platform_admins(
    db: DbSession,
    _: PlatformPrincipal,
) -> list[PlatformAdminResponse]:
    identities = ListPlatformAdmins(SqlAlchemyPlatformAdminRepository(db)).execute()
    return [PlatformAdminResponse.from_domain(identity) for identity in identities]


@router.post("", response_model=EnsurePlatformAdminResponse)
def ensure_platform_admin(
    payload: EnsurePlatformAdminRequest,
    response: Response,
    db: DbSession,
    principal: PlatformPrincipal,
) -> EnsurePlatformAdminResponse:
    try:
        result = EnsurePlatformAdmin(SqlAlchemyPlatformAdminRepository(db)).execute(
            EnsurePlatformAdminCommand(
                max_user_id=payload.max_user_id,
                full_name=payload.full_name,
            )
        )
    except ValueError as exc:
        raise bad_request(str(exc), code="invalid_platform_admin") from exc
    if result.identity.id is None:
        raise RuntimeError("Platform administrator was not persisted")
    db.add(
        AuditLog(
            admin_id=principal.admin_id,
            bot_instance_id=None,
            method="POST",
            path="/api/platform-admins",
            status_code=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
            meta={
                "action": "platform_admin_ensured",
                "target_admin_id": result.identity.id,
                "created": result.created,
                "promoted": result.previous_role not in {None, "platform_admin"},
                "reactivated": result.reactivated,
                "previous_role": result.previous_role,
            },
        )
    )
    db.commit()
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return EnsurePlatformAdminResponse.from_result(result)
