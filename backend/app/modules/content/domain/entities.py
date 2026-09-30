from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ContentCategory:
    id: int | None
    bot_instance_id: int
    slug: str
    icon: str
    parent_id: int | None = None
    order: int = 0
    is_active: bool = True
    published_version_id: int | None = None
    last_published_revision: int = 0
    is_home: bool = False
    # A capability shortcut: both set means this row is a live pointer into an installed
    # capability's view instead of a content page -- it has no draft/version, and `title`/
    # `subtitle`/`image_url` below (rather than a draft) carry its card display text.
    capability_key: str | None = None
    capability_view_key: str | None = None
    title: str | None = None
    subtitle: str | None = None
    image_url: str | None = None

    @property
    def is_shortcut(self) -> bool:
        return self.capability_key is not None and self.capability_view_key is not None


@dataclass(frozen=True, slots=True)
class ContentDraft:
    category_id: int
    title: str
    subtitle: str | None = None
    language: str = "ru"
    blocks: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 0
    is_shared: bool = False
    is_filled: bool = False
    image_url: str | None = None
    header_visible: bool = True


@dataclass(frozen=True, slots=True)
class SharedContentDraft:
    source_bot_instance_id: int
    source_bot_name: str
    category: ContentCategory
    draft: ContentDraft


@dataclass(frozen=True, slots=True)
class ContentVersion:
    id: int | None
    category_id: int
    version: int
    source_revision: int
    title: str
    subtitle: str | None
    language: str
    blocks: list[dict[str, Any]]
    is_filled: bool
    image_url: str | None
    header_visible: bool
    published_by: int | None
    published_at: datetime


@dataclass(frozen=True, slots=True)
class PublishedContent:
    category: ContentCategory
    # None only for a capability shortcut category, which has no version to publish.
    version: ContentVersion | None


@dataclass(frozen=True, slots=True)
class AttachmentReference:
    category_id: int
    usage: str  # "card_image" | "file_list_item"


@dataclass(frozen=True, slots=True)
class ContentAttachment:
    id: int
    name: str
    mime: str
    size_bytes: int
    created_at: datetime
    referenced_by_draft: tuple[AttachmentReference, ...] = ()
    referenced_by_published: tuple[AttachmentReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ContentAttachmentPage:
    items: list[ContentAttachment]
    total: int


@dataclass(frozen=True, slots=True)
class DeletedAttachment:
    id: int
    name: str
    mime: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ContentFormOption:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class ContentTestOption:
    id: int
    name: str
