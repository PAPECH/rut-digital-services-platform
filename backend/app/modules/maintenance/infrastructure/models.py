from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class MaintenancePolicyRecord(Base, TimestampMixin):
    __tablename__ = "maintenance_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    bot_instance_id: Mapped[int | None] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="off")
    title: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer)
    allow_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
