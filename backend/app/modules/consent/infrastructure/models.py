from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin
from ....models.enums import SystemEnum
from ..domain.entities import ConsentEventType


class UserConsentRecord(Base, TimestampMixin):
    """Current consent cycle -- see ConsentState. Survives the identity's own deletion:
    `user_id` is `ON DELETE SET NULL`, never CASCADE (Task 064)."""

    __tablename__ = "user_consents"
    __table_args__ = (
        UniqueConstraint("external_user_id", "system", name="uq_user_consents_external_system"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    external_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    system: Mapped[SystemEnum] = mapped_column(
        Enum(SystemEnum, name="system_enum"), nullable=False
    )

    given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_version: Mapped[str | None] = mapped_column(String(32))


class ConsentEventRecord(Base):
    """Append-only history -- the actual compliance evidence, mirrors FormSubmission /
    SubmissionStatusHistory. Never mutated, never deleted alongside the identity it
    describes."""

    __tablename__ = "consent_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_consent_id: Mapped[int] = mapped_column(
        ForeignKey("user_consents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[ConsentEventType] = mapped_column(
        Enum(
            ConsentEventType,
            name="consent_event_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_version: Mapped[str | None] = mapped_column(String(32))


class ConsentFunnelCounterRecord(Base):
    """Fully anonymous consent-funnel counter -- no user identifier of any kind, by design
    (see docs/tasks/064, 'Metrics for people who haven't consented yet'). One row per
    (bot, event type, day); `count` is incremented via an upsert, never per-event inserts."""

    __tablename__ = "consent_funnel_counters"

    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), primary_key=True
    )
    event_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ConsentNoticeRecord(Base, TimestampMixin):
    """Platform-wide (not per-bot) consent-prompt text, editable by a platform admin --
    unlike `app_settings` (bot_instances module), which hard-requires a bot_instance_id and
    is deliberately not reused here since the consent notice is the same across every bot
    (consent itself is global, Task 064). `key` is either a language code ("ru"/"en", whose
    `value` is the full HTML text shown in the bot chat -- mirrors how
    `bot_start_message_ru`/`_en` already work, just platform-wide instead of per-bot) or one
    of the `policy_*` keys (Task 066) holding the consent policy document's source (an
    external URL, or an uploaded file's storage path/name/mime) -- reused as a generic
    key/value store rather than adding a second single-purpose table for one more field."""

    __tablename__ = "consent_notice_texts"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
