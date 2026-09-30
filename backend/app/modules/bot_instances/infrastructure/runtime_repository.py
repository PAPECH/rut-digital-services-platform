from __future__ import annotations

from sqlalchemy.orm import Session

from ....services.bot_runtime_auth import hash_runtime_token
from .models import BotInstanceRecord, BotRuntimeRecord


def get_or_create_runtime(db: Session, bot_id: int) -> BotRuntimeRecord | None:
    if db.get(BotInstanceRecord, bot_id) is None:
        return None
    runtime = db.get(BotRuntimeRecord, bot_id)
    if runtime is None:
        runtime = BotRuntimeRecord(bot_instance_id=bot_id)
        db.add(runtime)
        db.flush()
    return runtime


class SqlAlchemyBotRuntimeBinder:
    """Infrastructure adapter binding a provisioned managed credential to a runtime record."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def bind_managed_credential(
        self,
        bot_id: int,
        credential_env_key: str,
        runtime_token: str,
    ) -> None:
        runtime = get_or_create_runtime(self._db, bot_id)
        if runtime is None:
            raise LookupError(bot_id)
        runtime.credential_source = "managed"
        runtime.credential_env_key = credential_env_key
        runtime.mode = "polling"
        runtime.runtime_token_hash = hash_runtime_token(runtime_token)
        runtime.last_seen_at = None
        runtime.last_error_code = None
