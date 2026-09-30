from __future__ import annotations

from typing import Any


def profile_disabled_with_required_fields(
    settings: dict[str, Any],
    profile_schema: list[dict[str, Any]],
) -> bool:
    """True when this settings/profile_schema combination is invalid: profile.enabled is
    false while at least one profile field is still marked required (Task 054). Pure and
    framework-free — settings/profile_schema are the plain dicts BotInstance already stores,
    not the Pydantic BotSettings/ProfileFieldDefinition models those come from.

    Callers pass the *effective* post-write state of the whole bot, not just what one
    request changed — profile.enabled and profile_schema are writable from two different
    endpoints (bot-admin PATCH .../current/settings vs platform-admin PATCH .../{bot_id}),
    so either write must be validated against the other field's current stored value.
    """
    profile_enabled = (settings.get("profile") or {}).get("enabled", True)
    if profile_enabled:
        return False
    return any(bool(field.get("required")) for field in profile_schema)
