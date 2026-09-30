from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....modules.admins.infrastructure.models import Admin
    from ....modules.profiles.infrastructure.models import User

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....db.base import Base, TimestampMixin
from ....models.enums import MessageDirectionEnum, SystemEnum
from ....modules.knowledge_base.domain.entities import MessageAiClassificationEnum


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("bot_instance_id", "external_id", name="uq_messages_bot_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    system: Mapped[SystemEnum] = mapped_column(
        Enum(
            SystemEnum,
            name="system_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        index=True,
        nullable=False,
    )
    direction: Mapped[MessageDirectionEnum] = mapped_column(
        Enum(
            MessageDirectionEnum,
            name="message_direction_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    text: Mapped[str | None] = mapped_column(Text)
    attachments: Mapped[list | None] = mapped_column(JSONB)

    is_ai_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_classification: Mapped[MessageAiClassificationEnum | None] = mapped_column(
        Enum(
            MessageAiClassificationEnum,
            name="message_ai_classification_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
    )
    # Документ, который был авто-отвечен/выбран из кандидатов для этого сообщения —
    # заменяет прежний паттерн "id внутри строки" (kb:{id}/kb_selected:{id}).
    # ON DELETE SET NULL: история сообщений не должна исчезать при удалении документа.
    kb_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="SET NULL"), index=True
    )

    replied_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    replied_by_admin: Mapped["Admin | None"] = relationship("Admin", lazy="joined")

    external_id: Mapped[str | None] = mapped_column(String(120))

    @property
    def replied_by_admin_name(self) -> str | None:
        return self.replied_by_admin.full_name if self.replied_by_admin else None


class StaffFavorite(Base, TimestampMixin):
    """Избранные обращения/пользователи у сотрудника поддержки."""

    __tablename__ = "staff_favorites"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "user_id",
            "support_id",
            name="uq_staff_favorites_bot_user_support",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    support_id: Mapped[int] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="favorited_by")
    support: Mapped["Admin"] = relationship(back_populates="favorites")
