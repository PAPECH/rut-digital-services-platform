from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Literal, Protocol

from ..domain.runtime_credentials import (
    managed_bot_token_env_key,
    runtime_token_env_key,
    validate_bot_token,
    webhook_secret_env_key,
)


class RuntimeCredentialStore(Protocol):
    def contains(self, key: str) -> bool: ...

    def get(self, key: str) -> str | None: ...

    def set_many(self, values: dict[str, str]) -> None: ...

    def delete_many(self, keys: list[str]) -> None: ...


def resolve_bot_token(
    *,
    credential_source: str | None,
    credential_env_key: str | None,
    store: RuntimeCredentialStore,
    legacy_fallback_token: str | None = None,
) -> str | None:
    """Resolve a bot's current real MAX token for signature verification (Task 036).

    Single source of truth for the env-then-managed-store lookup that both initData verification
    and the admin runtime-status endpoint need -- previously duplicated inline in
    `bot_instances/presentation/runtime_router.py` as a boolean-only check, which is how the
    per-bot resolution went unused by verification for as long as it did.

    `legacy_fallback_token`: for the pre-Task-013 convention where the platform's original bot's
    token lives in the plain `MAX_BOT_TOKEN` setting rather than a per-bot key -- the caller
    (presentation layer) supplies that value explicitly rather than this application-layer
    function reaching into global settings itself.
    """
    if not credential_env_key:
        return None
    if credential_source == "managed":
        return store.get(credential_env_key)
    value = os.environ.get(credential_env_key)
    if value:
        return value
    if credential_env_key == "MAX_BOT_TOKEN":
        return legacy_fallback_token or None
    return None


class ManagedBotTokenMissing(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProvisionManagedCredentialCommand:
    bot_slug: str
    bot_token: str | None
    mode: Literal["polling", "webhook"]


@dataclass(frozen=True, slots=True)
class ProvisionedManagedCredential:
    credential_env_key: str
    runtime_token: str


class ProvisionManagedCredential:
    def __init__(self, store: RuntimeCredentialStore) -> None:
        self._store = store

    def execute(
        self,
        command: ProvisionManagedCredentialCommand,
    ) -> ProvisionedManagedCredential:
        credential_key = managed_bot_token_env_key(command.bot_slug)
        values: dict[str, str] = {}
        if command.bot_token:
            values[credential_key] = validate_bot_token(command.bot_token)
        elif not self._store.contains(credential_key):
            raise ManagedBotTokenMissing("MAX bot token has not been saved")

        runtime_token = secrets.token_urlsafe(32)
        values[runtime_token_env_key(command.bot_slug)] = runtime_token
        if command.mode == "webhook":
            values[webhook_secret_env_key(command.bot_slug)] = secrets.token_urlsafe(32)
        self._store.set_many(values)
        return ProvisionedManagedCredential(
            credential_env_key=credential_key,
            runtime_token=runtime_token,
        )
