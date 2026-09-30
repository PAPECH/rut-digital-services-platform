import os

import pytest

from app.modules.bot_instances.application.runtime_credentials import (
    ManagedBotTokenMissing,
    ProvisionManagedCredential,
    ProvisionManagedCredentialCommand,
    resolve_bot_token,
)
from app.modules.bot_instances.domain.runtime_credentials import (
    managed_bot_token_env_key,
    runtime_token_env_key,
    webhook_secret_env_key,
)
from app.modules.bot_instances.infrastructure.env_file_credentials import (
    EnvFileRuntimeCredentialStore,
)


def test_managed_credentials_are_persisted_without_returning_bot_token(tmp_path) -> None:
    path = tmp_path / "secrets" / "bots.env"
    store = EnvFileRuntimeCredentialStore(path)

    result = ProvisionManagedCredential(store).execute(
        ProvisionManagedCredentialCommand(
            bot_slug="hr-services",
            bot_token="max-token-value-long-enough",
            mode="webhook",
        )
    )

    assert result.credential_env_key == "MAX_BOT_TOKEN_HR_SERVICES"
    assert result.runtime_token
    assert store.contains(managed_bot_token_env_key("hr-services"))
    assert store.contains(runtime_token_env_key("hr-services"))
    assert store.contains(webhook_secret_env_key("hr-services"))
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_managed_connection_requires_token_on_first_configuration(tmp_path) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")

    with pytest.raises(ManagedBotTokenMissing):
        ProvisionManagedCredential(store).execute(
            ProvisionManagedCredentialCommand(
                bot_slug="hr-services",
                bot_token=None,
                mode="polling",
            )
        )


# Task 036: `resolve_bot_token` is the single per-bot MAX-token lookup reused by initData
# verification and the admin runtime-status endpoint -- a bot's real token must resolve from
# ITS OWN configured source, never someone else's.


def test_resolve_bot_token_reads_managed_store(tmp_path) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")
    store.set_many({"MAX_BOT_TOKEN_HR_SERVICES": "hr-bots-own-token"})

    resolved = resolve_bot_token(
        credential_source="managed",
        credential_env_key="MAX_BOT_TOKEN_HR_SERVICES",
        store=store,
    )

    assert resolved == "hr-bots-own-token"


def test_resolve_bot_token_managed_store_missing_key_returns_none(tmp_path) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")

    resolved = resolve_bot_token(
        credential_source="managed",
        credential_env_key="MAX_BOT_TOKEN_NEVER_SET",
        store=store,
    )

    assert resolved is None


def test_resolve_bot_token_reads_real_env_var_for_environment_source(tmp_path, monkeypatch) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")
    monkeypatch.setenv("MAX_BOT_TOKEN_SCHOOL", "school-bots-own-token")

    resolved = resolve_bot_token(
        credential_source="environment",
        credential_env_key="MAX_BOT_TOKEN_SCHOOL",
        store=store,
    )

    assert resolved == "school-bots-own-token"


def test_resolve_bot_token_does_not_cross_bots(tmp_path, monkeypatch) -> None:
    """Regression for the real bug: a bot's token must never fall back to a DIFFERENT bot's
    value just because that other value happens to be configured somewhere."""
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")
    store.set_many({"MAX_BOT_TOKEN_HELPER": "helpers-own-token"})
    monkeypatch.delenv("MAX_BOT_TOKEN_SCHOOL", raising=False)

    resolved = resolve_bot_token(
        credential_source="environment",
        credential_env_key="MAX_BOT_TOKEN_SCHOOL",
        store=store,
        legacy_fallback_token="helpers-own-token",  # the legacy fallback only applies to the
        # literal "MAX_BOT_TOKEN" key, never to another bot's per-slug key.
    )

    assert resolved is None


def test_resolve_bot_token_legacy_fallback_only_for_plain_max_bot_token_key(tmp_path, monkeypatch) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")
    monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)

    resolved = resolve_bot_token(
        credential_source="environment",
        credential_env_key="MAX_BOT_TOKEN",
        store=store,
        legacy_fallback_token="the-legacy-admin-login-bots-token",
    )

    assert resolved == "the-legacy-admin-login-bots-token"


def test_resolve_bot_token_missing_credential_env_key_returns_none(tmp_path) -> None:
    store = EnvFileRuntimeCredentialStore(tmp_path / "bots.env")

    assert resolve_bot_token(credential_source=None, credential_env_key=None, store=store) is None
