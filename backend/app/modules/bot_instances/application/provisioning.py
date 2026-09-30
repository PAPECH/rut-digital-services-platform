from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..domain.entities import BotInstance
from ..domain.repositories import BotInstanceRepository
from ..domain.runtime_credentials import managed_bot_token_env_key, runtime_token_env_key
from .commands import CreateBotInstanceCommand
from .runtime_credentials import (
    ProvisionManagedCredential,
    ProvisionManagedCredentialCommand,
    RuntimeCredentialStore,
)
from .use_cases import CreateBotInstance

log = logging.getLogger(__name__)


class BotRuntimeBinder(Protocol):
    def bind_managed_credential(
        self,
        bot_id: int,
        credential_env_key: str,
        runtime_token: str,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ProvisionBotInstanceCommand:
    create: CreateBotInstanceCommand
    bot_token: str


class ProvisionBotInstance:
    """Create a bot instance and provision its managed MAX-token in one step.

    Keeps token/runtime-token generation entirely server-side so an admin only
    ever supplies a name and a token.
    """

    def __init__(
        self,
        bot_repository: BotInstanceRepository,
        credential_store: RuntimeCredentialStore,
        runtime_binder: BotRuntimeBinder,
    ) -> None:
        self._bot_repository = bot_repository
        self._credential_store = credential_store
        self._runtime_binder = runtime_binder

    def execute(self, command: ProvisionBotInstanceCommand) -> BotInstance:
        bot = CreateBotInstance(self._bot_repository).execute(command.create)
        assert bot.id is not None
        provisioned = ProvisionManagedCredential(self._credential_store).execute(
            ProvisionManagedCredentialCommand(
                bot_slug=bot.slug,
                bot_token=command.bot_token,
                mode="polling",
            )
        )
        try:
            self._runtime_binder.bind_managed_credential(
                bot.id,
                provisioned.credential_env_key,
                provisioned.runtime_token,
            )
        except Exception:
            # The credential was already written to disk (ProvisionManagedCredential is not part
            # of the DB transaction the caller commits/rolls back). Best-effort undo so a failure
            # here doesn't leave a live secret keyed to a bot instance that never persisted.
            try:
                self._credential_store.delete_many(
                    [managed_bot_token_env_key(bot.slug), runtime_token_env_key(bot.slug)]
                )
            except Exception:
                log.exception(
                    "Failed to roll back managed credential for bot slug %r after provisioning error",
                    bot.slug,
                )
            raise
        return bot
