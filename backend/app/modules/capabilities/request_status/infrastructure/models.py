from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .....db.base import Base, TimestampMixin


class RequestStatusStateRecord(Base, TimestampMixin):
    __tablename__ = "request_status_states"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "request_number_hash",
            name="uq_request_status_state_bot_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_number: Mapped[str] = mapped_column(String(64), nullable=False)
    request_number_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    last_status: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RequestStatusSubscriptionRecord(Base, TimestampMixin):
    __tablename__ = "request_status_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "user_id",
            "request_number_hash",
            name="uq_request_status_subscription_owner_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("capability_installations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_number: Mapped[str] = mapped_column(String(64), nullable=False)
    request_number_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
