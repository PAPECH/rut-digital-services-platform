from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CreateBotInstanceCommand:
    slug: str
    name: str
    description: str | None = None
    is_active: bool = True
    order: int = 0
    branding: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    profile_schema: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class UpdateBotInstanceCommand:
    bot_id: int
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    order: int | None = None
    branding: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    profile_schema: list[dict[str, Any]] | None = None
