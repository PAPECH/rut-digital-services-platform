from typing import Literal

import jwt
from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from ..core.errors import forbidden, unauthorized
from ..core.security import decode_token
from ..db.session import get_db

UserRole = Literal["student", "employee", "admin", "platform_admin"]


class CurrentPrincipal:
    def __init__(
        self,
        sub: str,
        role: UserRole,
        system: str | None,
        user_id: int | None,
        admin_id: int | None,
        bot_instance_id: int | None = None,
        bot_slug: str | None = None,
    ):
        self.sub = sub
        self.role: UserRole = role
        self.system = system
        self.user_id = user_id
        self.admin_id = admin_id
        self.bot_instance_id = bot_instance_id
        self.bot_slug = bot_slug

    @property
    def is_staff(self) -> bool:
        return self.role in ("employee", "admin", "platform_admin")

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "platform_admin")

    @property
    def is_platform_admin(self) -> bool:
        return self.role == "platform_admin"


def _decode(token: str) -> dict:
    try:
        return decode_token(token)
    except jwt.PyJWTError as e:
        raise unauthorized(f"Невалидный токен: {e!s}") from e


def get_current_principal(
    authorization: str | None = Header(default=None),
    session: str | None = Cookie(default=None),
) -> CurrentPrincipal:
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif session:
        token = session
    if not token:
        raise unauthorized("Требуется авторизация")

    payload = _decode(token)
    role = payload.get("role")
    if role not in ("student", "employee", "admin", "platform_admin"):
        raise unauthorized("Неизвестная роль в токене")
    return CurrentPrincipal(
        sub=str(payload.get("sub", "")),
        role=role,
        system=payload.get("system"),
        user_id=payload.get("user_pk"),
        admin_id=payload.get("admin_id"),
        bot_instance_id=payload.get("bot_instance_id"),
        bot_slug=payload.get("bot_slug"),
    )


def require_student(p: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
    if p.role != "student":
        raise forbidden("Только для студента")
    return p


def require_staff(p: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
    if not p.is_staff:
        raise forbidden("Только для сотрудников/админов")
    return p


def require_admin(p: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
    if not p.is_admin:
        raise forbidden("Только для админа")
    return p


def require_platform_admin(p: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
    if not p.is_platform_admin:
        raise forbidden("Только для администратора платформы")
    return p


DbSession = Session


def db_session() -> DbSession:  # type: ignore[empty-body]
    """Plain alias for FastAPI Depends signature readability."""
    yield from get_db()  # type: ignore[misc]
