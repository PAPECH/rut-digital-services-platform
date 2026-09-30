from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from ..modules.profiles.infrastructure.models import User


class UserAction(Base, TimestampMixin):
    __tablename__ = "user_actions"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_user_actions_event_id"),
        Index("ix_user_actions_bot_created", "bot_instance_id", "created_at"),
        Index("ix_user_actions_type_created", "action_type", "created_at"),
        Index("ix_user_actions_user_bot_created", "user_id", "bot_instance_id", "created_at"),
        Index("ix_user_actions_category_created", "category_id", "created_at"),
        Index("ix_user_actions_form_created", "form_template_id", "created_at"),
        Index("ix_user_actions_capability_created", "capability_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=lambda: str(uuid4()),
    )
    session_id: Mapped[str | None] = mapped_column(String(36))

    source_surface: Mapped[str | None] = mapped_column(String(32))
    interaction_kind: Mapped[str | None] = mapped_column(String(64))

    category_id: Mapped[int | None] = mapped_column(Integer)
    source_category_id: Mapped[int | None] = mapped_column(Integer)
    content_version_id: Mapped[int | None] = mapped_column(Integer)
    block_id: Mapped[str | None] = mapped_column(String(64))
    item_id: Mapped[str | None] = mapped_column(String(64))
    tabs_block_id: Mapped[str | None] = mapped_column(String(64))
    tab_key: Mapped[str | None] = mapped_column(String(64))

    form_template_id: Mapped[int | None] = mapped_column(Integer)
    form_version_id: Mapped[int | None] = mapped_column(Integer)
    faq_id: Mapped[int | None] = mapped_column(Integer)
    news_id: Mapped[int | None] = mapped_column(Integer)
    attachment_id: Mapped[int | None] = mapped_column(Integer)

    capability_installation_id: Mapped[int | None] = mapped_column(Integer)
    capability_key: Mapped[str | None] = mapped_column(String(64))
    capability_view_key: Mapped[str | None] = mapped_column(String(64))
    outcome_code: Mapped[str | None] = mapped_column(String(64))

    # Compatibility-only fields. New analytics writes use typed columns above.
    description: Mapped[str | None] = mapped_column(Text)

    payload: Mapped[dict | None] = mapped_column(JSON)

    user: Mapped["User"] = relationship(back_populates="actions")
