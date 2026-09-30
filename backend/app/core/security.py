import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from functools import lru_cache
from typing import Any

import jwt

from .config import settings


def create_access_token(payload: dict[str, Any], expires_min: int | None = None) -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(minutes=expires_min or settings.JWT_EXPIRES_MIN)
    return jwt.encode({**payload, "exp": exp}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


class HmacPurpose(StrEnum):
    """Every non-JWT signed-capability artifact this app mints, each with its own derived key
    (see `_subkey` below) — Task 053 audit finding: these used to all HMAC directly with the
    raw JWT_SECRET, so a leak of one purpose's signing capability leaked all of them at once.
    JWT signing itself intentionally keeps using the raw secret via PyJWT (not this module) —
    deriving a subkey for it too would invalidate every already-issued access/session token
    (up to `JWT_EXPIRES_MIN`/`ADMIN_SESSION_ABSOLUTE_DAYS` old) the moment this ships, which is
    a much larger blast radius than re-minting a signed file URL or re-provisioning a bot
    runtime token — treated as a deliberately separate, out-of-scope concern here."""

    FILE_URL = "file_url"
    CONTENT_PREVIEW = "content_preview"
    BOT_RUNTIME_TOKEN = "bot_runtime_token"
    RATE_LIMIT_IDENTITY = "rate_limit_identity"
    ADMIN_REFRESH_TOKEN = "admin_refresh_token"
    ADMIN_INVITE_TOKEN = "admin_invite_token"


def _hkdf_sha256(ikm: bytes, info: bytes, length: int = 32) -> bytes:
    """Minimal RFC 5869 HKDF (SHA-256). A constant zero salt is standard/safe here since the
    single high-entropy input (JWT_SECRET, length-checked by core.config's production
    validator) is the only secret material — HKDF's salt exists to combine multiple
    lower-entropy sources, which doesn't apply to a single already-random secret."""
    prk = hmac.new(b"\x00" * hashlib.sha256().digest_size, ikm, hashlib.sha256).digest()
    okm = b""
    previous = b""
    counter = 1
    while len(okm) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        okm += previous
        counter += 1
    return okm[:length]


@lru_cache(maxsize=None)
def _subkey(purpose: HmacPurpose) -> bytes:
    return _hkdf_sha256(settings.JWT_SECRET.encode("utf-8"), purpose.value.encode("utf-8"))


def hmac_sign(purpose: HmacPurpose, message: str) -> str:
    """HMAC-SHA256 signature using a key derived from JWT_SECRET for exactly this `purpose` —
    replaces the old shared-raw-secret primitive (see `HmacPurpose` docstring)."""
    return hmac.new(_subkey(purpose), message.encode("utf-8"), hashlib.sha256).hexdigest()


def hmac_verify(purpose: HmacPurpose, message: str, signature: str) -> bool:
    return hmac.compare_digest(hmac_sign(purpose, message), signature)
