from __future__ import annotations

from datetime import datetime
from typing import Any

from ..domain.entities import NewsItem
from ..domain.repositories import NewsRepository


class CreateNewsItem:
    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        bot_instance_id: int,
        title: str,
        title_en: str | None,
        body_blocks: list[dict[str, Any]],
        category: str | None,
        cover_attachment_id: int | None,
        is_active: bool,
        published_at: datetime | None,
    ) -> NewsItem:
        item = NewsItem(
            id=None,
            bot_instance_id=bot_instance_id,
            title=title,
            title_en=title_en,
            body_blocks=body_blocks,
            category=category,
            cover_attachment_id=cover_attachment_id,
            is_active=is_active,
            published_at=published_at,
        )
        return self._repository.add(item)


class ListNewsItems:
    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, *, include_inactive: bool) -> list[NewsItem]:
        return self._repository.list_for_bot(bot_instance_id, include_inactive=include_inactive)


class GetNewsItem:
    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, item_id: int) -> NewsItem | None:
        return self._repository.get(bot_instance_id, item_id)


class UpdateNewsItem:
    """Applies a partial change set (only explicitly-provided fields) on top of the current item,
    then re-validates the merged result as a whole new `NewsItem` -- there is no separate draft or
    published state for a single news item; a successful patch takes effect immediately."""

    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, item_id: int, changes: dict[str, Any]) -> NewsItem | None:
        current = self._repository.get(bot_instance_id, item_id)
        if current is None:
            return None
        merged = NewsItem(
            id=current.id,
            bot_instance_id=current.bot_instance_id,
            title=changes.get("title", current.title),
            title_en=changes.get("title_en", current.title_en),
            body_blocks=changes.get("body_blocks", current.body_blocks),
            category=changes.get("category", current.category),
            cover_attachment_id=changes.get("cover_attachment_id", current.cover_attachment_id),
            is_active=changes.get("is_active", current.is_active),
            published_at=changes.get("published_at", current.published_at),
        )
        return self._repository.patch(bot_instance_id, item_id, merged)


class DeleteNewsItem:
    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, item_id: int) -> bool:
        return self._repository.delete(bot_instance_id, item_id)
