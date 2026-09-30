from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TimestampMixin
from .enums import SystemEnum


class MonitoringSubscription(Base, TimestampMixin):
    __tablename__ = "monitoring_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "request_number", name="uq_monitoring_user_request"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    system: Mapped[SystemEnum] = mapped_column(
        Enum(SystemEnum, name="system_enum"), index=True, nullable=False
    )
    request_number: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MonitoringState(Base):
    __tablename__ = "monitoring_states"

    request_number: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_status: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
