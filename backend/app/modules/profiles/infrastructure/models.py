from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....db.base import Base, TimestampMixin
from ....models.enums import SystemEnum

if TYPE_CHECKING:
    from ....models.logger import UserAction
    from ...support_chat.infrastructure.models import StaffFavorite


class BotMembershipRecord(Base, TimestampMixin):
    __tablename__ = "bot_memberships"
    __table_args__ = (UniqueConstraint("bot_instance_id", "user_id", name="uq_bot_membership_bot_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    local_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ban_chat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_chat_reason: Mapped[str | None] = mapped_column(Text)
    ban_forms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_forms_reason: Mapped[str | None] = mapped_column(Text)
    ban_app: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_app_reason: Mapped[str | None] = mapped_column(Text)
    source_campaign_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaign_links.id", ondelete="SET NULL"), index=True
    )


class User(Base, TimestampMixin):
    """Студент. Разделение по `system`."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("user_id", "system", name="uq_users_user_id_system"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    system: Mapped[SystemEnum] = mapped_column(
        Enum(SystemEnum, name="system_enum"), index=True, nullable=False
    )

    last_name: Mapped[str | None] = mapped_column(String(120))
    first_name: Mapped[str | None] = mapped_column(String(120))
    patronymic: Mapped[str | None] = mapped_column(String(120))
    username: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32))
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email: Mapped[str | None] = mapped_column(String(180))
    photo_url: Mapped[str | None] = mapped_column(String(512))
    language_code: Mapped[str | None] = mapped_column(String(16), default="ru")

    birth_date: Mapped[date | None] = mapped_column(Date)
    study_group: Mapped[str | None] = mapped_column(String(64))
    rut_personnel_number: Mapped[str | None] = mapped_column(String(64))

    # Единый профиль для всех ботов платформы.
    job_title: Mapped[str | None] = mapped_column(String(240))
    structural_unit: Mapped[str | None] = mapped_column(String(500))
    shared_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    ban_chat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_chat_reason: Mapped[str | None] = mapped_column(Text)
    ban_forms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_forms_reason: Mapped[str | None] = mapped_column(Text)
    ban_app: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_app_reason: Mapped[str | None] = mapped_column(Text)

    actions: Mapped[list["UserAction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    favorited_by: Mapped[list["StaffFavorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
