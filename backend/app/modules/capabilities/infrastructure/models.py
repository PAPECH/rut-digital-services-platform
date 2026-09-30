from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class CapabilityInstallationRecord(Base, TimestampMixin):
    __tablename__ = "capability_installations"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "capability_key",
            name="uq_capability_installation_bot_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    capability_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    config_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    configured_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    enabled_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    last_health_status: Mapped[str] = mapped_column(String(24), default="unconfigured", nullable=False)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_error_code: Mapped[str | None] = mapped_column(Text)
