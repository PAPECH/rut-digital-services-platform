from __future__ import annotations

from typing import Protocol

from .entities import NewsItem


class NewsRepository(Protocol):
    def add(self, item: NewsItem) -> NewsItem: ...

    def get(self, bot_instance_id: int, item_id: int) -> NewsItem | None: ...

    def list_for_bot(self, bot_instance_id: int, *, include_inactive: bool) -> list[NewsItem]: ...

    def patch(self, bot_instance_id: int, item_id: int, merged: NewsItem) -> NewsItem | None: ...

    def delete(self, bot_instance_id: int, item_id: int) -> bool: ...
