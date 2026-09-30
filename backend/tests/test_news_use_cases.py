from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.modules.news.application.use_cases import (
    CreateNewsItem,
    DeleteNewsItem,
    ListNewsItems,
    UpdateNewsItem,
)
from app.modules.news.domain.entities import NewsItem

_PARAGRAPH = {"id": "p1", "type": "paragraph", "text": "Текст новости"}


class InMemoryNewsRepository:
    def __init__(self) -> None:
        self._items: dict[int, NewsItem] = {}
        self._next_id = 1

    def add(self, item: NewsItem) -> NewsItem:
        item = replace(item, id=self._next_id, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        self._items[item.id] = item
        self._next_id += 1
        return item

    def get(self, bot_instance_id: int, item_id: int) -> NewsItem | None:
        item = self._items.get(item_id)
        if item is None or item.bot_instance_id != bot_instance_id:
            return None
        return item

    def list_for_bot(self, bot_instance_id: int, *, include_inactive: bool) -> list[NewsItem]:
        items = [item for item in self._items.values() if item.bot_instance_id == bot_instance_id]
        if not include_inactive:
            items = [item for item in items if item.is_active]
        return sorted(items, key=lambda item: (item.published_at, item.id), reverse=True)

    def patch(self, bot_instance_id: int, item_id: int, merged: NewsItem) -> NewsItem | None:
        current = self.get(bot_instance_id, item_id)
        if current is None:
            return None
        updated = replace(merged, created_at=current.created_at, updated_at=datetime.now(UTC))
        self._items[item_id] = updated
        return updated

    def delete(self, bot_instance_id: int, item_id: int) -> bool:
        current = self.get(bot_instance_id, item_id)
        if current is None:
            return False
        del self._items[item_id]
        return True


def _create(repo: InMemoryNewsRepository, **overrides) -> NewsItem:
    params = {
        "bot_instance_id": 1,
        "title": "Заголовок",
        "title_en": None,
        "body_blocks": [_PARAGRAPH],
        "category": None,
        "cover_attachment_id": None,
        "is_active": True,
        "published_at": None,
    }
    params.update(overrides)
    return CreateNewsItem(repo).execute(**params)


def test_create_news_item_persists_and_is_listed() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo)
    assert item.id == 1
    listed = ListNewsItems(repo).execute(1, include_inactive=False)
    assert listed == [item]


def test_list_news_items_excludes_inactive_by_default_for_students() -> None:
    repo = InMemoryNewsRepository()
    _create(repo, is_active=False)
    assert ListNewsItems(repo).execute(1, include_inactive=False) == []
    assert len(ListNewsItems(repo).execute(1, include_inactive=True)) == 1


def test_list_news_items_orders_newest_first() -> None:
    repo = InMemoryNewsRepository()
    older = _create(repo, published_at=datetime(2026, 1, 1, tzinfo=UTC))
    newer = _create(repo, published_at=datetime(2026, 6, 1, tzinfo=UTC))
    listed = ListNewsItems(repo).execute(1, include_inactive=True)
    assert listed == [newer, older]


def test_list_news_items_is_tenant_scoped() -> None:
    repo = InMemoryNewsRepository()
    _create(repo, bot_instance_id=1)
    _create(repo, bot_instance_id=2)
    assert len(ListNewsItems(repo).execute(1, include_inactive=True)) == 1
    assert len(ListNewsItems(repo).execute(2, include_inactive=True)) == 1


def test_update_news_item_applies_only_provided_fields() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo, category="Спорт")
    updated = UpdateNewsItem(repo).execute(1, item.id, {"title": "Новый заголовок"})
    assert updated.title == "Новый заголовок"
    assert updated.category == "Спорт"


def test_update_news_item_can_clear_optional_field() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo, category="Спорт")
    updated = UpdateNewsItem(repo).execute(1, item.id, {"category": None})
    assert updated.category is None


def test_update_news_item_returns_none_for_wrong_tenant() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo, bot_instance_id=1)
    assert UpdateNewsItem(repo).execute(2, item.id, {"title": "x"}) is None


def test_delete_news_item_removes_it() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo)
    assert DeleteNewsItem(repo).execute(1, item.id) is True
    assert ListNewsItems(repo).execute(1, include_inactive=True) == []


def test_delete_news_item_denies_cross_tenant() -> None:
    repo = InMemoryNewsRepository()
    item = _create(repo, bot_instance_id=1)
    assert DeleteNewsItem(repo).execute(2, item.id) is False
