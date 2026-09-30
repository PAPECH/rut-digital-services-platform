from __future__ import annotations

from typing import Any, TypedDict


class KbThresholdOverrides(TypedDict):
    auto_answer_threshold: float | None
    candidate_min_threshold: float | None
    max_candidates: int | None


def kb_overrides(bot_settings: dict[str, Any] | None) -> KbThresholdOverrides:
    """Читает per-bot переопределения порогов KB-матчинга из сырого
    BotInstance.settings (JSONB). Отсутствующий раздел/поле — не ошибка,
    MatchKnowledgeBase трактует None как «взять платформенное значение по умолчанию»."""
    section = (bot_settings or {}).get("knowledge_base") or {}
    return {
        "auto_answer_threshold": section.get("auto_answer_threshold"),
        "candidate_min_threshold": section.get("candidate_min_threshold"),
        "max_candidates": section.get("max_candidates"),
    }
