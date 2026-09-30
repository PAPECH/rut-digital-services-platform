from __future__ import annotations

from typing import Any


def student_text_enabled(bot_settings: dict[str, Any] | None) -> bool:
    """True (по умолчанию) сохраняет сегодняшнее поведение для любого бота, у
    которого этот раздел настроек ещё не сохранялся."""
    section = (bot_settings or {}).get("chat") or {}
    value = section.get("student_text_enabled")
    return True if value is None else bool(value)
