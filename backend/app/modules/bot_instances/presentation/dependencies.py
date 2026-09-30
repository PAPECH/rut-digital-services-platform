from dataclasses import dataclass

import jwt
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal
from ....core.errors import forbidden, not_found, unauthorized
from ....core.security import decode_token
from ....db.session import get_db
from ....services.bot_runtime_auth import authorize_bot_runtime
from ...tenancy.presentation.dependencies import resolve_tenant
from ..application.access_control import admin_has_bot_permission
from ..domain.entities import BotInstance
from ..infrastructure.models import AdminBotAccessRecord


@dataclass(frozen=True, slots=True)
class StaffManagementContext:
    bot_id: int
    principal: CurrentPrincipal


def require_staff_management(
    bot: BotInstance = Depends(resolve_tenant),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> StaffManagementContext:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    if not principal.is_admin:
        raise forbidden("Staff management permission is required", code="staff_management_denied")
    if not admin_has_bot_permission(db, principal, bot.id, "can_manage_staff"):
        raise forbidden("Staff management permission is required", code="staff_management_denied")
    return StaffManagementContext(bot.id, principal)


def authorize_setting_read(
    x_bot_token: str | None,
    x_bot_runtime_token: str | None,
    authorization: str | None,
    bot_instance_id: int,
    db: Session,
) -> None:
    """Доступ на чтение: X-Bot-Token (для бота) ИЛИ JWT (любая авторизованная роль)."""
    if x_bot_token or x_bot_runtime_token:
        authorize_bot_runtime(db, bot_instance_id, x_bot_runtime_token, x_bot_token)
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized("Нужна авторизация или X-Bot-Token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise unauthorized(f"Невалидный токен: {e!s}") from e
    role = payload.get("role")
    if role == "platform_admin":
        return
    if role == "student" and payload.get("bot_instance_id") == bot_instance_id:
        return
    admin_id = payload.get("admin_id")
    if role in {"employee", "admin"} and admin_id:
        access = db.execute(
            select(AdminBotAccessRecord.id).where(
                AdminBotAccessRecord.admin_id == admin_id,
                AdminBotAccessRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if access is not None:
            return
    raise forbidden("Токен не имеет доступа к выбранному боту", code="tenant_access_denied")
