from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ....core.errors import bad_request, not_found
from ....db.session import get_db
from ...bot_instances.presentation.dependencies import (
    StaffManagementContext,
    require_staff_management,
)
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
from .schemas import AdminInviteResponse, CreateBotInviteRequest, CreatedAdminInviteResponse

router = APIRouter()

_PATH = "/api/instances/current/admin-invites"


@router.get("/current/admin-invites", response_model=list[AdminInviteResponse])
def list_bot_invites(
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> list[AdminInviteResponse]:
    invites = ListAdminInvites(SqlAlchemyAdminInviteRepository(db)).execute(
        "bot_staff", context.bot_id
    )
    return [AdminInviteResponse.from_domain(invite) for invite in invites]


@router.post(
    "/current/admin-invites", response_model=CreatedAdminInviteResponse, status_code=201
)
def create_bot_invite(
    payload: CreateBotInviteRequest,
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> CreatedAdminInviteResponse:
    try:
        result = CreateAdminInvite(
            SqlAlchemyAdminInviteRepository(db), HmacInviteTokenCodec()
        ).execute(
            CreateAdminInviteCommand(
                kind="bot_staff",
                bot_instance_id=context.bot_id,
                full_name=payload.full_name,
                staff_role=payload.role,
                permissions=payload.permissions.to_domain(),
                ttl_hours=payload.ttl_hours,
                max_uses=payload.max_uses,
                created_by_admin_id=context.principal.admin_id,
            ),
            now=datetime.now(tz=UTC),
        )
    except ValueError as exc:
        raise bad_request(str(exc), code="invalid_invite") from exc
    db.add(
        invite_audit_entry(
            action="admin_invite_created",
            invite=result.invite,
            actor_admin_id=context.principal.admin_id,
            method="POST",
            path=_PATH,
            status_code=201,
        )
    )
    db.commit()
    return CreatedAdminInviteResponse.from_result(result)


@router.delete("/current/admin-invites/{invite_id}", status_code=204)
def revoke_bot_invite(
    invite_id: int,
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> Response:
    try:
        invite = RevokeAdminInvite(SqlAlchemyAdminInviteRepository(db)).execute(
            RevokeAdminInviteCommand(
                invite_id=invite_id, kind="bot_staff", bot_instance_id=context.bot_id
            ),
            now=datetime.now(tz=UTC),
        )
    except AdminInviteNotFound as exc:
        raise not_found("Invite not found", code="invite_not_found") from exc
    db.add(
        invite_audit_entry(
            action="admin_invite_revoked",
            invite=invite,
            actor_admin_id=context.principal.admin_id,
            method="DELETE",
            path=f"{_PATH}/{invite_id}",
            status_code=204,
        )
    )
    db.commit()
    return Response(status_code=204)
