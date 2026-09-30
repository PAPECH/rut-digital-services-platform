"""Signed, self-contained preview tokens for the admin content builder (Task 024).

A token encodes `bot_instance_id.category_id.exp.nonce.sig` — no DB storage, matching the
signed-URL pattern already used for file downloads (see `services/files.py`), sharing the same
underlying HMAC primitive (`core.security.hmac_sign`/`hmac_verify`).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from ..core.security import HmacPurpose, hmac_sign, hmac_verify

DEFAULT_PREVIEW_TTL_SECONDS = 15 * 60


class InvalidPreviewToken(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PreviewTokenPayload:
    bot_instance_id: int
    category_id: int
    expires_at: int


def make_preview_token(
    *,
    bot_instance_id: int,
    category_id: int,
    ttl_seconds: int = DEFAULT_PREVIEW_TTL_SECONDS,
) -> tuple[str, int]:
    """Returns (token, expires_at_unix)."""
    exp = int(time.time()) + ttl_seconds
    nonce = secrets.token_urlsafe(8)
    sig = _sign(bot_instance_id, category_id, exp, nonce)
    return f"{bot_instance_id}.{category_id}.{exp}.{nonce}.{sig}", exp


def verify_preview_token(token: str) -> PreviewTokenPayload:
    parts = token.split(".")
    if len(parts) != 5:
        raise InvalidPreviewToken("Malformed preview token")
    bot_id_s, category_id_s, exp_s, nonce, sig = parts
    try:
        bot_instance_id, category_id, exp = int(bot_id_s), int(category_id_s), int(exp_s)
    except ValueError as exc:
        raise InvalidPreviewToken("Malformed preview token") from exc
    if exp < int(time.time()):
        raise InvalidPreviewToken("Preview link expired")
    if not hmac_verify(HmacPurpose.CONTENT_PREVIEW, f"{bot_instance_id}.{category_id}.{exp}.{nonce}", sig):
        raise InvalidPreviewToken("Invalid preview token signature")
    return PreviewTokenPayload(bot_instance_id=bot_instance_id, category_id=category_id, expires_at=exp)


def _sign(bot_instance_id: int, category_id: int, exp: int, nonce: str) -> str:
    return hmac_sign(HmacPurpose.CONTENT_PREVIEW, f"{bot_instance_id}.{category_id}.{exp}.{nonce}")
