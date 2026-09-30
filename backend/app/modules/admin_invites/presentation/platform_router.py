from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin
from ....core.errors import bad_request, not_found
from ....db.session import get_db
from ..application.commands import CreateAdminInviteCommand, RevokeAdminInviteCommand
from ..application.use_cases import (
    AdminInviteNotFound,
    CreateAdminInvite,
    ListAdminInvites,
    RevokeAdminInvite,
)
from ..infrastructure.repository import SqlAlchemyAdminInviteRepository
from ..infrastructure.token_codec import HmacInviteTokenCodec
from .audit import invite_audit_entry
from .schemas import (
    AdminInviteResponse,
    CreatedAdminInviteResponse,
    CreatePlatformInviteRequest,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
PlatformPrincipal = Annotated[CurrentPrincipal, Depends(require_platform_admin)]

_PATH = "/api/platform-admins/invites"


@router.get("/invites", response_model=list[AdminInviteResponse])
def list_platform_invites(db: DbSession, _: PlatformPrincipal) -> list[AdminInviteResponse]:
    invites = ListAdminInvites(SqlAlchemyAdminInviteRepository(db)).execute("platform", None)
    return [AdminInviteResponse.from_domain(invite) for invite in invites]


@router.post("/invites", response_model=CreatedAdminInviteResponse, status_code=201)
def create_platform_invite(
    payload: CreatePlatformInviteRequest,
    db: DbSession,
    principal: PlatformPrincipal,
) -> CreatedAdminInviteResponse:
    try:
        result = CreateAdminInvite(
            SqlAlchemyAdminInviteRepository(db), HmacInviteTokenCodec()
        ).execute(
            CreateAdminInviteCommand(
                kind="platform",
                bot_instance_id=None,
                full_name=payload.full_name,
                staff_role=None,
                permissions=None,
                ttl_hours=payload.ttl_hours,
                max_uses=payload.max_uses,
                created_by_admin_id=principal.admin_id,
            ),
            now=datetime.now(tz=UTC),
        )
    except ValueError as exc:
        raise bad_request(str(exc), code="invalid_invite") from exc
    db.add(
        invite_audit_entry(
            action="admin_invite_created",
            invite=result.invite,
            actor_admin_id=principal.admin_id,
            method="POST",
            path=_PATH,
            status_code=201,
        )
    )
    db.commit()
    return CreatedAdminInviteResponse.from_result(result)


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_platform_invite(
    invite_id: int,
    db: DbSession,
    principal: PlatformPrincipal,
) -> Response:
    try:
        invite = RevokeAdminInvite(SqlAlchemyAdminInviteRepository(db)).execute(
            RevokeAdminInviteCommand(invite_id=invite_id, kind="platform", bot_instance_id=None),
            now=datetime.now(tz=UTC),
        )
    except AdminInviteNotFound as exc:
        raise not_found("Invite not found", code="invite_not_found") from exc
    db.add(
        invite_audit_entry(
            action="admin_invite_revoked",
            invite=invite,
            actor_admin_id=principal.admin_id,
            method="DELETE",
            path=f"{_PATH}/{invite_id}",
            status_code=204,
        )
    )
    db.commit()
    return Response(status_code=204)
