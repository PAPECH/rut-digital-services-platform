from __future__ import annotations

from typing import Protocol

from .entities import ContentCategory, ContentDraft, PublishedContent, SharedContentDraft


class ContentRepository(Protocol):
    def list_categories(
        self, bot_instance_id: int
    ) -> list[tuple[ContentCategory, ContentDraft | None]]: ...

    def list_published(self, bot_instance_id: int) -> list[PublishedContent]: ...

    def list_shared_drafts(self) -> list[SharedContentDraft]: ...

    def get_shared_draft(self, category_id: int) -> SharedContentDraft | None: ...

    def get_category(self, bot_instance_id: int, category_id: int) -> ContentCategory | None: ...

    def get_home_category(self, bot_instance_id: int) -> ContentCategory | None: ...

    def get_category_by_slug(self, bot_instance_id: int, slug: str) -> ContentCategory | None: ...

    def get_published_by_slug(self, bot_instance_id: int, slug: str) -> PublishedContent | None: ...

    def get_published_by_category(
        self, bot_instance_id: int, category_id: int
    ) -> PublishedContent | None: ...

    def get_draft(self, bot_instance_id: int, category_id: int) -> ContentDraft | None: ...

    def create_category(
        self,
        category: ContentCategory,
        draft: ContentDraft | None,
        *,
        created_by: int | None,
    ) -> tuple[ContentCategory, ContentDraft | None]: ...

    def update_category(self, category: ContentCategory) -> ContentCategory: ...

    def save_draft(
        self,
        bot_instance_id: int,
        draft: ContentDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> ContentDraft: ...

    def publish(
        self,
        bot_instance_id: int,
        category_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedContent: ...

    def reorder(self, bot_instance_id: int, category_ids: list[int]) -> list[ContentCategory]: ...
