from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Setting:
    bot_instance_id: int
    key: str
    value: str | None
