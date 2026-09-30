from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_platform_admin
from ....core.errors import bad_request, conflict, forbidden, not_found
from ....db.session import get_db
from ..application.admin_use_cases import (
    AdminAccountAlreadyExists,
    AdminAccountNotFound,
    CannotModifyOwnPrivileges,
    CreateAdminAccount,
    DeleteAdminAccount,
    UpdateAdminAccount,
)
from ..domain.admin_account import AdminRoleEnum
from ..infrastructure.repositories import SqlAlchemyAdminAccountRepository
from .schemas import AdminCreateIn, AdminOut, AdminPatchIn

router = APIRouter()


@router.get("", response_model=list[AdminOut])
def list_admins(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_platform_admin),
) -> list[AdminOut]:
    accounts = SqlAlchemyAdminAccountRepository(db).list_all()
    return [AdminOut.from_domain(account) for account in accounts]


@router.post("", response_model=AdminOut, status_code=201)
def create_admin(
    payload: AdminCreateIn,
    db: Session = Depends(get_db),
    principal: CurrentPrincipal = Depends(require_platform_admin),
) -> AdminOut:
    max_user_id = payload.max_user_id.strip()
    full_name = payload.full_name.strip()
    if not max_user_id or not full_name:
        raise bad_request("max_user_id и full_name обязательны")
    if payload.role == AdminRoleEnum.platform_admin and not principal.is_platform_admin:
        raise forbidden("Только администратор платформы может назначить эту роль")
    try:
        account = CreateAdminAccount(SqlAlchemyAdminAccountRepository(db)).execute(
            max_user_id=max_user_id,
            full_name=full_name,
            role=payload.role.value,
            is_active=payload.is_active,
        )
    except AdminAccountAlreadyExists as exc:
        raise conflict("Сотрудник с таким max_user_id уже существует") from exc
    return AdminOut.from_domain(account)


@router.patch("/{admin_id}", response_model=AdminOut)
def patch_admin(
    admin_id: int,
    payload: AdminPatchIn,
    db: Session = Depends(get_db),
    me: CurrentPrincipal = Depends(require_platform_admin),
) -> AdminOut:
    repository = SqlAlchemyAdminAccountRepository(db)
    current = repository.get(admin_id)
    if current is None:
        raise not_found("Сотрудник не найден")

    touches_platform_role = AdminRoleEnum.platform_admin in {current.role, payload.role}
    if touches_platform_role and not me.is_platform_admin:
        raise forbidden("Только администратор платформы может изменять эту роль")

    changes = payload.model_dump(exclude_unset=True)
    try:
        updated = UpdateAdminAccount(repository).execute(
            admin_id, changes, actor_admin_id=me.admin_id
        )
    except AdminAccountNotFound as exc:
        raise not_found("Сотрудник не найден") from exc
    except CannotModifyOwnPrivileges as exc:
        raise bad_request(str(exc)) from exc
    return AdminOut.from_domain(updated)


@router.delete("/{admin_id}", status_code=204)
def delete_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    me: CurrentPrincipal = Depends(require_platform_admin),
):
    repository = SqlAlchemyAdminAccountRepository(db)
    current = repository.get(admin_id)
    if current is None:
        raise not_found("Сотрудник не найден")
    if current.role == AdminRoleEnum.platform_admin and not me.is_platform_admin:
        raise forbidden("Только администратор платформы может удалить эту учётную запись")
    try:
        DeleteAdminAccount(repository).execute(admin_id, actor_admin_id=me.admin_id)
    except AdminAccountNotFound as exc:
        raise not_found("Сотрудник не найден") from exc
    except CannotModifyOwnPrivileges as exc:
        raise bad_request(str(exc)) from exc
