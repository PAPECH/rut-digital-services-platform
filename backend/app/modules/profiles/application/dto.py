from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..domain.entities import BotMembership, SharedProfile


@dataclass(frozen=True, slots=True)
class BotProfile:
    shared: SharedProfile
    membership: BotMembership


@dataclass(frozen=True, slots=True)
class UpdateBotProfileCommand:
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    email: str | None = None
    birth_date: date | None = None
    custom_data: dict[str, Any] = field(default_factory=dict)
