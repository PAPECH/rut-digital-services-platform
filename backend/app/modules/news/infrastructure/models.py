from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class NewsItemRecord(Base, TimestampMixin):
    __tablename__ = "news_items"
    __table_args__ = (
        Index("ix_news_items_bot_published", "bot_instance_id", "published_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(300))
    body_blocks: Mapped[list] = mapped_column(JSONB, nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    cover_attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
