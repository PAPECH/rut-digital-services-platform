from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class BotInstanceRecord(Base, TimestampMixin):
    __tablename__ = "bot_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Uniqueness is enforced by a partial index (uq_bot_instances_slug_live, WHERE
    # deleted_at IS NULL) so a soft-deleted bot's slug can be reused by a new bot.
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    branding: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    profile_schema: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminBotAccessRecord(Base, TimestampMixin):
    __tablename__ = "admin_bot_access"
    __table_args__ = (UniqueConstraint("admin_id", "bot_instance_id", name="uq_admin_bot_access"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    can_process_submissions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_manage_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_forms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_maintenance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_capabilities: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_campaigns: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_form_tests: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)


class BotRuntimeRecord(Base, TimestampMixin):
    __tablename__ = "bot_runtimes"

    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), primary_key=True
    )
    credential_env_key: Mapped[str | None] = mapped_column(String(120))
    credential_source: Mapped[str | None] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(20), default="polling", nullable=False)
    runtime_token_hash: Mapped[str | None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    username: Mapped[str | None] = mapped_column(String(120))
    max_bot_id: Mapped[str | None] = mapped_column(String(120))
    runtime_version: Mapped[str | None] = mapped_column(String(120))
    last_error_code: Mapped[str | None] = mapped_column(String(120))
