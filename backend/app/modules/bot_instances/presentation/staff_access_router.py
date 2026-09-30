from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ....core.errors import bad_request, conflict, not_found
from ....db.session import get_db
from ..application.staff_access_commands import (
    GrantStaffAccessCommand,
    RevokeStaffAccessCommand,
    UpdateStaffAccessCommand,
)
from ..application.staff_access_use_cases import (
    CannotRemoveOwnStaffManagement,
    GrantBotStaffAccess,
    ListBotStaffAccess,
    RevokeBotStaffAccess,
    StaffAccessAlreadyExists,
    StaffAccessNotFound,
    StaffIdentityInactive,
    UpdateBotStaffAccess,
)
from ..infrastructure.staff_access_repository import SqlAlchemyStaffAccessRepository
from .dependencies import StaffManagementContext, require_staff_management
from .staff_access_schemas import (
    GrantStaffAccessRequest,
    StaffAccessResponse,
    UpdateStaffAccessRequest,
)

router = APIRouter()


@router.get("/current/staff-access", response_model=list[StaffAccessResponse])
def list_staff_access(
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> list[StaffAccessResponse]:
    items = ListBotStaffAccess(SqlAlchemyStaffAccessRepository(db)).execute(context.bot_id)
    return [StaffAccessResponse.from_domain(item) for item in items]


@router.post("/current/staff-access", response_model=StaffAccessResponse, status_code=201)
def grant_staff_access(
    payload: GrantStaffAccessRequest,
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> StaffAccessResponse:
    use_case = GrantBotStaffAccess(SqlAlchemyStaffAccessRepository(db))
    try:
        access = use_case.execute(
            GrantStaffAccessCommand(
                bot_instance_id=context.bot_id,
                max_user_id=payload.max_user_id,
                full_name=payload.full_name,
                role=payload.role,
                permissions=payload.permissions.to_domain(),
            )
        )
    except StaffAccessAlreadyExists as exc:
        raise conflict("This staff member already has access to the bot", code="staff_access_exists") from exc
    except StaffIdentityInactive as exc:
        raise conflict("The staff account is inactive", code="staff_identity_inactive") from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    db.commit()
    return StaffAccessResponse.from_domain(access)


@router.patch("/current/staff-access/{access_id}", response_model=StaffAccessResponse)
def update_staff_access(
    access_id: int,
    payload: UpdateStaffAccessRequest,
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> StaffAccessResponse:
    if context.principal.admin_id is None:
        actor_admin_id = -1
    else:
        actor_admin_id = context.principal.admin_id
    try:
        access = UpdateBotStaffAccess(SqlAlchemyStaffAccessRepository(db)).execute(
            UpdateStaffAccessCommand(
                bot_instance_id=context.bot_id,
                access_id=access_id,
                actor_admin_id=actor_admin_id,
                permissions=payload.permissions.to_domain(),
            )
        )
    except StaffAccessNotFound as exc:
        raise not_found("Staff access not found", code="staff_access_not_found") from exc
    except CannotRemoveOwnStaffManagement as exc:
        raise bad_request(
            "You cannot remove your own staff-management permission",
            code="cannot_demote_self",
        ) from exc
    db.commit()
    return StaffAccessResponse.from_domain(access)


@router.delete("/current/staff-access/{access_id}", status_code=204)
def revoke_staff_access(
    access_id: int,
    context: StaffManagementContext = Depends(require_staff_management),
    db: Session = Depends(get_db),
) -> Response:
    actor_admin_id = context.principal.admin_id or -1
    try:
        RevokeBotStaffAccess(SqlAlchemyStaffAccessRepository(db)).execute(
            RevokeStaffAccessCommand(
                bot_instance_id=context.bot_id,
                access_id=access_id,
                actor_admin_id=actor_admin_id,
            )
        )
    except StaffAccessNotFound as exc:
        raise not_found("Staff access not found", code="staff_access_not_found") from exc
    except CannotRemoveOwnStaffManagement as exc:
        raise bad_request("You cannot revoke your own access", code="cannot_revoke_self") from exc
    db.commit()
    return Response(status_code=204)

