from __future__ import annotations

import hmac

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import unauthorized
from ..core.security import HmacPurpose, hmac_sign, hmac_verify
from ..modules.bot_instances.infrastructure.models import BotRuntimeRecord


def hash_runtime_token(token: str) -> str:
    return hmac_sign(HmacPurpose.BOT_RUNTIME_TOKEN, token)


def authorize_bot_runtime(
    db: Session,
    bot_instance_id: int,
    runtime_token: str | None,
    legacy_token: str | None,
) -> None:
    """Authenticate a bot process already bound to the server-resolved tenant."""
    runtime = db.get(BotRuntimeRecord, bot_instance_id)
    if runtime is not None and runtime.runtime_token_hash:
        if not runtime_token or not hmac_verify(
            HmacPurpose.BOT_RUNTIME_TOKEN, runtime_token, runtime.runtime_token_hash
        ):
            raise unauthorized("Неверный runtime token", code="invalid_bot_runtime_token")
        return

    expected = settings.BOT_INTERNAL_API_TOKEN
    if expected and legacy_token and hmac.compare_digest(legacy_token, expected):
        return
    if not expected and settings.APP_ENV != "production":
        return
    raise unauthorized("Неверный internal bot token", code="invalid_internal_bot_token")


def authorize_bot_supervisor(legacy_token: str | None) -> None:
    """Authorize the process supervisor without granting access to any tenant data."""
    expected = settings.BOT_INTERNAL_API_TOKEN
    if expected and legacy_token and hmac.compare_digest(legacy_token, expected):
        return
    if not expected and settings.APP_ENV != "production":
        return
    raise unauthorized("Неверный internal bot token", code="invalid_internal_bot_token")
