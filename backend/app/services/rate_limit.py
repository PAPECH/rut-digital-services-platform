from __future__ import annotations

import logging
import re
from typing import Callable

import jwt
from fastapi import Request

from ..core.config import settings
from ..core.errors import ApiError
from ..core.security import HmacPurpose, decode_token, hmac_sign
from ..db.redis import redis_client

log = logging.getLogger(__name__)

_BOT_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")


def _tenant_key(value: str | None) -> str:
    slug = (value or settings.DEFAULT_BOT_SLUG).strip().lower()
    return slug if _BOT_SLUG_RE.fullmatch(slug) else "invalid"


def opaque_rate_identity(namespace: str, value: str) -> str:
    digest = hmac_sign(HmacPurpose.RATE_LIMIT_IDENTITY, f"{namespace}:{value}")[:32]
    return f"{namespace}:{digest}"


def max_user_rate_identity(system: str, external_user_id: str) -> str:
    return opaque_rate_identity("max-user", f"{system}:{external_user_id}")


def _session_identity(request: Request) -> str:
    authorization = request.headers.get("authorization")
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("session")
    if not token:
        return "anonymous"
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return "invalid-session"
    subject = str(payload.get("sub") or "")
    return opaque_rate_identity("session", subject) if subject else "invalid-session"


def enforce_rate_limit(
    name: str,
    *,
    limit: int,
    window_seconds: int,
    tenant: str | None,
    identity: str,
) -> None:
    try:
        key = f"rl:{name}:{_tenant_key(tenant)}:{identity}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window_seconds)
        if count > limit:
            ttl = redis_client.ttl(key)
            raise ApiError(
                code="rate_limited",
                message="Слишком много запросов, попробуйте позже",
                status_code=429,
                retry_after=ttl if isinstance(ttl, int) and ttl > 0 else window_seconds,
            )
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("rate_limit %s: redis error: %s", name, exc)


def rate_limit(
    name: str,
    *,
    limit: int,
    window_seconds: int,
    key_func: Callable[[Request], str] | None = None,
):
    def _resolve_key(request: Request) -> str:
        if key_func is not None:
            return opaque_rate_identity("custom", key_func(request))
        return _session_identity(request)

    def _dep(request: Request) -> None:
        enforce_rate_limit(
            name,
            limit=limit,
            window_seconds=window_seconds,
            tenant=request.headers.get("x-bot-slug"),
            identity=_resolve_key(request),
        )

    return _dep
