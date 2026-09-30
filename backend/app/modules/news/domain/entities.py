from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .body import validate_news_body

TITLE_MAX_LENGTH = 300
CATEGORY_MAX_LENGTH = 120


class InvalidNewsItem(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NewsItem:
    id: int | None
    bot_instance_id: int
    title: str
    body_blocks: list[dict[str, Any]]
    title_en: str | None = None
    category: str | None = None
    cover_attachment_id: int | None = None
    is_active: bool = True
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        title = self.title.strip() if isinstance(self.title, str) else ""
        if not title:
            raise InvalidNewsItem("Title cannot be empty")
        if len(title) > TITLE_MAX_LENGTH:
            raise InvalidNewsItem(f"Title exceeds {TITLE_MAX_LENGTH} characters")
        object.__setattr__(self, "title", title)

        title_en = self.title_en.strip() if self.title_en else None
        if title_en and len(title_en) > TITLE_MAX_LENGTH:
            raise InvalidNewsItem(f"Title (EN) exceeds {TITLE_MAX_LENGTH} characters")
        object.__setattr__(self, "title_en", title_en or None)

        category = self.category.strip() if self.category else None
        if category and len(category) > CATEGORY_MAX_LENGTH:
            raise InvalidNewsItem(f"Category exceeds {CATEGORY_MAX_LENGTH} characters")
        object.__setattr__(self, "category", category or None)

        if self.cover_attachment_id is not None and (
            not isinstance(self.cover_attachment_id, int) or self.cover_attachment_id <= 0
        ):
            raise InvalidNewsItem("Invalid cover attachment id")

        object.__setattr__(self, "body_blocks", validate_news_body(self.body_blocks))
        object.__setattr__(self, "published_at", self.published_at or datetime.now(UTC))
