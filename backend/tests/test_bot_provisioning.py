from __future__ import annotations

import pytest

from app.modules.bot_instances.application.commands import CreateBotInstanceCommand
from app.modules.bot_instances.application.provisioning import (
    ProvisionBotInstance,
    ProvisionBotInstanceCommand,
)
from app.modules.bot_instances.application.use_cases import BotSlugAlreadyExists
from app.modules.bot_instances.domain.runtime_credentials import (
    InvalidBotCredential,
    managed_bot_token_env_key,
)

from .test_bot_instances import InMemoryBotRepository


class InMemoryCredentialStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def contains(self, key: str) -> bool:
        return bool(self.values.get(key))

    def set_many(self, values: dict[str, str]) -> None:
        self.values.update(values)


class InMemoryRuntimeBinder:
    def __init__(self) -> None:
        self.bound: dict[int, tuple[str, str]] = {}

    def bind_managed_credential(
        self,
        bot_id: int,
        credential_env_key: str,
        runtime_token: str,
    ) -> None:
        self.bound[bot_id] = (credential_env_key, runtime_token)


def test_provision_creates_bot_and_stores_token_and_runtime_token_automatically() -> None:
    bot_repository = InMemoryBotRepository()
    credential_store = InMemoryCredentialStore()
    runtime_binder = InMemoryRuntimeBinder()
    use_case = ProvisionBotInstance(bot_repository, credential_store, runtime_binder)

    bot = use_case.execute(
        ProvisionBotInstanceCommand(
            create=CreateBotInstanceCommand(slug="hr-bot", name="Кадры"),
            bot_token="a" * 32,
        )
    )

    assert bot.id is not None
    expected_key = managed_bot_token_env_key("hr-bot")
    assert credential_store.values[expected_key] == "a" * 32

    bound_key, runtime_token = runtime_binder.bound[bot.id]
    assert bound_key == expected_key
    # The admin never chooses this value -- it must be generated server-side.
    assert runtime_token
    assert len(runtime_token) > 20


def test_provision_rejects_invalid_token_without_touching_credential_store() -> None:
    bot_repository = InMemoryBotRepository()
    credential_store = InMemoryCredentialStore()
    runtime_binder = InMemoryRuntimeBinder()
    use_case = ProvisionBotInstance(bot_repository, credential_store, runtime_binder)

    with pytest.raises(InvalidBotCredential):
        use_case.execute(
            ProvisionBotInstanceCommand(
                create=CreateBotInstanceCommand(slug="hr-bot", name="Кадры"),
                bot_token="short",
            )
        )

    assert credential_store.values == {}
    assert runtime_binder.bound == {}


def test_provision_rejects_duplicate_slug_before_touching_credential_store() -> None:
    bot_repository = InMemoryBotRepository()
    credential_store = InMemoryCredentialStore()
    runtime_binder = InMemoryRuntimeBinder()
    use_case = ProvisionBotInstance(bot_repository, credential_store, runtime_binder)
    use_case.execute(
        ProvisionBotInstanceCommand(
            create=CreateBotInstanceCommand(slug="hr-bot", name="Кадры"),
            bot_token="a" * 32,
        )
    )
    credential_store.values.clear()
    runtime_binder.bound.clear()

    with pytest.raises(BotSlugAlreadyExists):
        use_case.execute(
            ProvisionBotInstanceCommand(
                create=CreateBotInstanceCommand(slug="hr-bot", name="Дубликат"),
                bot_token="b" * 32,
            )
        )

    assert credential_store.values == {}
    assert runtime_binder.bound == {}
