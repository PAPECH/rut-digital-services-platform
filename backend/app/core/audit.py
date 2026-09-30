from __future__ import annotations

import logging
import re
import time

import jwt
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.security import decode_token
from ..db.session import SessionLocal
from ..modules.audit.infrastructure.models import AuditLog
from ..modules.bot_instances.infrastructure.models import BotInstanceRecord

log = logging.getLogger(__name__)

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_PREFIXES = (
    "/api/auth/",
    "/api/files",  # подписанные/публичные с подписью
    "/api/messages/ingress",
    "/api/messages/from-student",
)


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _principal_payload(request: Request) -> dict | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        return decode_token(token)
    except jwt.PyJWTError:
        return None


def _resolve_bot_id(db, request: Request) -> int | None:
    instance_match = re.match(r"^/api/instances/(\d+)(?:/|$)", request.url.path)
    if instance_match:
        bot_id = int(instance_match.group(1))
        if db.get(BotInstanceRecord, bot_id) is not None:
            return bot_id
    slug = request.headers.get("x-bot-slug")
    if not slug:
        return None
    return db.execute(
        select(BotInstanceRecord.id).where(
            BotInstanceRecord.slug == slug.strip().lower()
        )
    ).scalar_one_or_none()


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        method = request.method
        should_audit = (
            method in _MUTATING
            and path.startswith("/api/")
            and not any(path.startswith(p) for p in _SKIP_PREFIXES)
        )

        if not should_audit:
            return await call_next(request)

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        principal = _principal_payload(request)
        admin_id = principal.get("admin_id") if principal else None
        # Не пишем действия студентов в audit — они не сотрудники.
        if admin_id is None:
            return response

        try:
            with SessionLocal() as db:
                bot_instance_id = _resolve_bot_id(db, request)
                db.add(
                    AuditLog(
                        admin_id=admin_id,
                        bot_instance_id=bot_instance_id,
                        ip=_client_ip(request),
                        method=method,
                        path=path,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                    )
                )
                db.commit()
        except Exception as e:  # noqa: BLE001
            log.warning("audit write failed: %s", e)

        return response
