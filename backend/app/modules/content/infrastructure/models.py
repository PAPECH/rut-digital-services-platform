from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class ContentCategoryRecord(Base, TimestampMixin):
    __tablename__ = "content_categories"
    __table_args__ = (
        UniqueConstraint("bot_instance_id", "slug", name="uq_content_category_bot_slug"),
        CheckConstraint(
            "(capability_key IS NULL) = (capability_view_key IS NULL)",
            name="ck_content_category_capability_pair",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_categories.id", ondelete="SET NULL"),
        index=True,
    )
    icon: Mapped[str] = mapped_column(String(80), nullable=False, default="folder")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    published_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "content_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_content_category_published_version",
        )
    )

    last_published_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Uniqueness (at most one per bot) is enforced by the partial index
    # uq_content_categories_home_per_bot (WHERE is_home), not a column constraint.
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    # Capability shortcut pointer (Task 044) -- both set means this row has no draft/version and
    # is a live link into an installed capability's view; `title`/`subtitle`/`image_url` are then
    # its card display text (a normal category's title/subtitle/image live on its draft/version).
    capability_key: Mapped[str | None] = mapped_column(String(64))
    capability_view_key: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(300))
    subtitle: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)


class ContentDraftRecord(Base, TimestampMixin):
    __tablename__ = "content_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("content_categories.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru")
    blocks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_filled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    header_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))


class ContentAttachmentReferenceRecord(Base):
    """Tracks *current* draft/published usage of an admin-uploaded attachment, so deletion can be
    gated against "is this file still in the live published version" without scanning JSON at
    delete time (Task 025). Rows for a given (category_id, scope) are fully replaced whenever that
    draft is saved or that category is published -- this table has no history, only current state."""

    __tablename__ = "content_attachment_references"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "scope", "attachment_id", "usage", name="uq_content_attachment_reference"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attachment_id: Mapped[int] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("content_categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    usage: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContentVersionRecord(Base):
    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("category_id", "version", name="uq_content_version_category_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("content_categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru")
    blocks: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_filled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    header_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    published_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
