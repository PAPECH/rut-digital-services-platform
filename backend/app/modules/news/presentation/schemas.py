from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NewsItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    title_en: str | None = Field(default=None, max_length=300)
    body_blocks: list[dict[str, Any]] = Field(min_length=1)
    category: str | None = Field(default=None, max_length=120)
    cover_attachment_id: int | None = None
    is_active: bool = True
    published_at: datetime | None = None


class NewsItemPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    title_en: str | None = Field(default=None, max_length=300)
    body_blocks: list[dict[str, Any]] | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, max_length=120)
    cover_attachment_id: int | None = None
    is_active: bool | None = None
    published_at: datetime | None = None


class AttachmentUrlEntry(BaseModel):
    url: str
    mime: str


class NewsItemResponse(BaseModel):
    id: int
    bot_instance_id: int
    title: str
    title_en: str | None
    body_blocks: list[dict[str, Any]]
    category: str | None
    cover_attachment_id: int | None
    cover_url: str | None
    is_active: bool
    published_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
    # Resolves every `file_list` item's `attachment_id` inside `body_blocks` to a signed URL +
    # mime, the same way `content`'s published-category response resolves its own file blocks --
    # so the mini-app never needs a second round-trip per attachment.
    attachment_urls: dict[int, AttachmentUrlEntry]
