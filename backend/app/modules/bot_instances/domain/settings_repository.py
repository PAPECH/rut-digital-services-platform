from __future__ import annotations

from typing import Protocol

from .settings import Setting


class SettingRepository(Protocol):
    def get(self, bot_instance_id: int, key: str) -> Setting | None: ...

    def list_for_bot(self, bot_instance_id: int) -> list[Setting]: ...

    def upsert(self, bot_instance_id: int, key: str, value: str | None) -> Setting: ...

    def delete(self, bot_instance_id: int, key: str) -> bool: ...
