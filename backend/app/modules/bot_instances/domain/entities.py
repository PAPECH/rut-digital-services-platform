from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")


class InvalidBotInstance(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BotInstance:
    id: int | None
    slug: str
    name: str
    description: str | None = None
    is_active: bool = True
    order: int = 0
    branding: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    profile_schema: list[dict[str, Any]] = field(default_factory=list)
    deleted_at: datetime | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __post_init__(self) -> None:
        normalized_slug = self.slug.strip().lower()
        normalized_name = self.name.strip()
        if not _SLUG_RE.fullmatch(normalized_slug):
            raise InvalidBotInstance("Bot slug must contain 2-80 lowercase letters, digits, '_' or '-'")
        if not normalized_name:
            raise InvalidBotInstance("Bot name cannot be empty")
        object.__setattr__(self, "slug", normalized_slug)
        object.__setattr__(self, "name", normalized_name)
