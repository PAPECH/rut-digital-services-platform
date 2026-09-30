from __future__ import annotations

import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.config import settings
from ....core.errors import bad_request, forbidden, unauthorized
from ....core.security import create_access_token
from ....db.session import get_db
from ....services.max_validation import InitDataValidationError, validate_init_data
from ....services.rate_limit import (
    enforce_rate_limit,
    max_user_rate_identity,
    opaque_rate_identity,
)
from ...admin_invites.application.commands import RedeemAdminInviteCommand
from ...admin_invites.application.ports import InviteeInactive
from ...admin_invites.application.use_cases import AdminInviteInvalid, RedeemAdminInvite
from ...admin_invites.domain.start_param import parse_invite_token
from ...admin_invites.infrastructure.grants import UseCaseInviteGrants
from ...admin_invites.infrastructure.repository import SqlAlchemyAdminInviteRepository
from ...admin_invites.infrastructure.token_codec import HmacInviteTokenCodec
from ...admin_invites.presentation.audit import invite_audit_entry
from ...admins.infrastructure.models import Admin
from ..application.services import (
    RefreshReuseDetected,
    RefreshSessionExpired,
    RefreshSessionInvalid,
    RevokeAdminSession,
    RotateAdminSession,
    StartAdminSession,
)
from ..infrastructure.repositories import HmacRefreshTokenCodec, SqlAlchemyAdminSessionRepository
from .schemas import AdminLoginOut, AdminProfileOut, InitDataIn, TokenOut

router = APIRouter()


def _make_token(payload: dict, *, expires_min: int | None = None) -> TokenOut:
    lifetime = expires_min or settings.JWT_EXPIRES_MIN
    token = create_access_token(payload, expires_min=lifetime)
    return TokenOut(
        access_token=token,
        token_type="bearer",
        role=payload["role"],
        expires_at=datetime.now(tz=UTC) + timedelta(minutes=lifetime),
    )


def _admin_token(admin: Admin, *, system: str = "max") -> TokenOut:
    return _make_token(
        {
            "sub": f"a:{admin.id}",
            "role": admin.role.value,
            "admin_id": admin.id,
            "system": system,
        },
        expires_min=settings.ADMIN_ACCESS_EXPIRES_MIN,
    )


def _refresh_codec() -> HmacRefreshTokenCodec:
    return HmacRefreshTokenCodec()


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:64]
    return request.client.host[:64] if request.client else None


def _set_admin_cookies(response: Response, refresh_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)
    max_age = settings.ADMIN_REFRESH_EXPIRES_DAYS * 24 * 60 * 60
    common = {
        "secure": settings.is_production,
        "samesite": "lax",
        "max_age": max_age,
    }
    response.set_cookie(
        settings.ADMIN_REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        path="/api/auth",
        **common,
    )
    response.set_cookie(
        settings.ADMIN_CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        path="/",
        **common,
    )


def _clear_admin_cookies(response: Response) -> None:
    response.delete_cookie(settings.ADMIN_REFRESH_COOKIE_NAME, path="/api/auth")
    response.delete_cookie(settings.ADMIN_CSRF_COOKIE_NAME, path="/")


def _require_csrf(request: Request, csrf_header: str | None) -> None:
    csrf_cookie = request.cookies.get(settings.ADMIN_CSRF_COOKIE_NAME)
    if not csrf_header or not csrf_cookie or not hmac.compare_digest(csrf_header, csrf_cookie):
        raise forbidden("Проверка CSRF не пройдена", code="csrf_failed")


def _redeem_invite(db: Session, raw_token: str, max_user_id: str, ip: str | None) -> None:
    enforce_rate_limit(
        "admin_invite_redeem",
        limit=10,
        window_seconds=600,
        tenant="platform",
        identity=max_user_rate_identity("max", max_user_id),
    )
    if ip:
        enforce_rate_limit(
            "admin_invite_redeem_ip",
            limit=30,
            window_seconds=600,
            tenant="platform",
            identity=opaque_rate_identity("ip", ip),
        )
    try:
        redeemed = RedeemAdminInvite(
            SqlAlchemyAdminInviteRepository(db),
            HmacInviteTokenCodec(),
            UseCaseInviteGrants(db),
        ).execute(
            RedeemAdminInviteCommand(raw_token=raw_token, max_user_id=max_user_id),
            now=datetime.now(tz=UTC),
        )
    except AdminInviteInvalid as exc:
        db.rollback()
        raise forbidden("Приглашение недействительно", code="invite_invalid") from exc
    except InviteeInactive as exc:
        db.rollback()
        raise forbidden("Учётная запись сотрудника отключена", code="admin_inactive") from exc
    db.add(
        invite_audit_entry(
            action="admin_invite_redeemed",
            invite=redeemed.invite,
            actor_admin_id=redeemed.admin_id,
            method="POST",
            path="/api/auth/admin/login",
            status_code=200,
            extra={"target_admin_id": redeemed.admin_id, "created": redeemed.created},
        )
    )


@router.post(
    "/admin/login",
    response_model=AdminLoginOut,
)
def auth_admin_login(
    payload: InitDataIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AdminLoginOut:
    try:
        init = validate_init_data(payload.init_data, token=settings.MAX_BOT_TOKEN)
    except InitDataValidationError as e:
        raise unauthorized(str(e)) from e
    enforce_rate_limit(
        "auth_max",
        limit=60,
        window_seconds=60,
        tenant="platform",
        identity=max_user_rate_identity("max", init.user_id),
    )

    invite_token = parse_invite_token(init.start_param)
    if init.start_param and init.start_param != "admin_login" and invite_token is None:
        raise bad_request("Неверный start_param для входа в админку", code="bad_start_param")
    if invite_token is not None:
        _redeem_invite(db, invite_token, init.user_id, _request_ip(request))

    admin = db.execute(
        select(Admin).where(Admin.max_user_id == init.user_id, Admin.is_active.is_(True))
    ).scalar_one_or_none()

    if admin is None:
        raise forbidden("Этот аккаунт MAX не привязан к сотруднику платформы")

    issued = StartAdminSession(
        SqlAlchemyAdminSessionRepository(db),
        _refresh_codec(),
        refresh_days=settings.ADMIN_REFRESH_EXPIRES_DAYS,
        absolute_days=settings.ADMIN_SESSION_ABSOLUTE_DAYS,
    ).execute(
        admin.id,
        user_agent=request.headers.get("user-agent"),
        ip=_request_ip(request),
    )
    db.commit()
    _set_admin_cookies(response, issued.raw_token)
    return AdminLoginOut(
        token=_admin_token(admin, system=payload.system.value),
        admin=AdminProfileOut.model_validate(admin, from_attributes=True),
    )


@router.post("/admin/refresh", response_model=AdminLoginOut)
def auth_admin_refresh(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AdminLoginOut:
    _require_csrf(request, x_csrf_token)
    raw_token = request.cookies.get(settings.ADMIN_REFRESH_COOKIE_NAME)
    if not raw_token:
        raise unauthorized("Refresh-сессия отсутствует", code="refresh_missing")

    service = RotateAdminSession(
        SqlAlchemyAdminSessionRepository(db),
        _refresh_codec(),
        refresh_days=settings.ADMIN_REFRESH_EXPIRES_DAYS,
    )
    try:
        issued = service.execute(
            raw_token,
            user_agent=request.headers.get("user-agent"),
            ip=_request_ip(request),
        )
    except RefreshReuseDetected as exc:
        db.commit()
        _clear_admin_cookies(response)
        raise unauthorized(
            "Обнаружено повторное использование refresh-токена",
            code="refresh_reuse_detected",
        ) from exc
    except RefreshSessionExpired as exc:
        db.commit()
        _clear_admin_cookies(response)
        raise unauthorized("Refresh-сессия истекла", code="refresh_expired") from exc
    except RefreshSessionInvalid as exc:
        db.rollback()
        _clear_admin_cookies(response)
        raise unauthorized("Refresh-сессия недействительна", code="refresh_invalid") from exc

    admin = db.get(Admin, issued.session.admin_id)
    if admin is None or not admin.is_active:
        RevokeAdminSession(
            SqlAlchemyAdminSessionRepository(db),
            _refresh_codec(),
        ).execute(issued.raw_token)
        db.commit()
        _clear_admin_cookies(response)
        raise forbidden("Учётная запись сотрудника отключена", code="admin_inactive")

    db.commit()
    _set_admin_cookies(response, issued.raw_token)
    return AdminLoginOut(
        token=_admin_token(admin),
        admin=AdminProfileOut.model_validate(admin, from_attributes=True),
    )


@router.post("/admin/logout", status_code=204)
def auth_admin_logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    _require_csrf(request, x_csrf_token)
    raw_token = request.cookies.get(settings.ADMIN_REFRESH_COOKIE_NAME)
    if raw_token:
        RevokeAdminSession(
            SqlAlchemyAdminSessionRepository(db),
            _refresh_codec(),
        ).execute(raw_token)
        db.commit()
    _clear_admin_cookies(response)
    response.status_code = 204
    return response
