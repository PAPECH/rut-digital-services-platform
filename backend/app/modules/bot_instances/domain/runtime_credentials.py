from __future__ import annotations

import re


class InvalidBotCredential(ValueError):
    pass


def _slug_suffix(slug: str) -> str:
    suffix = re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_")
    if not suffix:
        raise InvalidBotCredential("Bot slug cannot produce an environment key")
    return suffix


def managed_bot_token_env_key(slug: str) -> str:
    return f"MAX_BOT_TOKEN_{_slug_suffix(slug)}"


def runtime_token_env_key(slug: str) -> str:
    return f"BOT_RUNTIME_TOKEN_{_slug_suffix(slug)}"


def webhook_secret_env_key(slug: str) -> str:
    return f"BOT_WEBHOOK_SECRET_{_slug_suffix(slug)}"


def validate_bot_token(token: str) -> str:
    value = token.strip()
    if len(value) < 16:
        raise InvalidBotCredential("MAX bot token is too short")
    if any(character in value for character in ("\n", "\r", "\x00")):
        raise InvalidBotCredential("MAX bot token contains invalid characters")
    return value
