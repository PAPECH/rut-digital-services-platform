from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class CampaignLinkRecord(Base, TimestampMixin):
    __tablename__ = "campaign_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(512), nullable=False)
    campaign: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    placement: Mapped[str] = mapped_column(String(200), nullable=False)
    target: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL")
    )
    open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # target: bot repeat-touch counter (Task 074) -- always 0 for target: webapp rows.
    repeat_open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignLinkOpenRecord(Base, TimestampMixin):
    __tablename__ = "campaign_link_opens"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    campaign_link_id: Mapped[int] = mapped_column(
        ForeignKey("campaign_links.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bot_membership_id: Mapped[int] = mapped_column(
        ForeignKey("bot_memberships.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CampaignLinkUnmatchedOpenRecord(Base, TimestampMixin):
    """A well-formed code (passes `validate_code`'s charset/length rule) that did not resolve to
    a non-deleted `campaign_links` row for this bot (Task 074) -- append-only, no update, no soft
    delete, never decomposed into campaign/source/placement (see Task 074's Non-goals)."""

    __tablename__ = "campaign_link_unmatched_opens"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(512), nullable=False)
    event_source: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
