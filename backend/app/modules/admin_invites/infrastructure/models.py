from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin


class AdminInviteRecord(Base, TimestampMixin):
    __tablename__ = "admin_invites"
    __table_args__ = (
        CheckConstraint("kind IN ('platform', 'bot_staff')", name="ck_admin_invites_kind"),
        CheckConstraint(
            "(kind = 'platform') = (bot_instance_id IS NULL)",
            name="ck_admin_invites_kind_bot",
        ),
        CheckConstraint(
            "used_count >= 0 AND used_count <= max_uses",
            name="ck_admin_invites_used_count",
        ),
        UniqueConstraint("token_hash", name="uq_admin_invites_token_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    bot_instance_id: Mapped[int | None] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    staff_role: Mapped[str | None] = mapped_column(String(16))
    permissions: Mapped[dict | None] = mapped_column(JSONB)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL")
    )
