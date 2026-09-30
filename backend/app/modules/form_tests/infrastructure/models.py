from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....db.base import Base, TimestampMixin
from ..domain.entities import TestAttemptStatus


class TestDefinitionRecord(Base, TimestampMixin):
    __tablename__ = "form_tests"
    __table_args__ = (UniqueConstraint("bot_instance_id", "slug", name="uq_form_tests_bot_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "form_test_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_form_tests_published_version",
        )
    )
    last_published_revision: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    draft: Mapped[TestDraftRecord | None] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="TestDraftRecord.test_definition_id",
    )
    versions: Mapped[list[TestVersionRecord]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        foreign_keys="TestVersionRecord.test_definition_id",
        order_by="TestVersionRecord.version",
    )


class TestDraftRecord(Base, TimestampMixin):
    __tablename__ = "form_test_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_definition_id: Mapped[int] = mapped_column(
        ForeignKey("form_tests.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    intro_text: Mapped[str | None] = mapped_column(Text)
    schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    # Participation-consent checkbox (Task 073) -- a *live* reference to this bot's document
    # library; `ON DELETE SET NULL` so deleting a referenced document never fails, it just leaves
    # the draft's reference dangling until an admin fixes it or turns consent off (caught at the
    # next save/publish, never silently).
    consent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("form_test_consent_documents.id", ondelete="SET NULL")
    )
    consent_checkbox_text: Mapped[str | None] = mapped_column(Text)

    # Per-test attempt settings (Task 075) -- independent of each other and of consent above.
    allow_retake: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_attempt_history: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_scores: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    definition: Mapped[TestDefinitionRecord] = relationship(
        back_populates="draft", foreign_keys=[test_definition_id]
    )


class TestVersionRecord(Base):
    __tablename__ = "form_test_versions"
    __table_args__ = (
        UniqueConstraint("test_definition_id", "version", name="uq_form_test_versions_definition_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    test_definition_id: Mapped[int] = mapped_column(
        ForeignKey("form_tests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    intro_text: Mapped[str | None] = mapped_column(Text)
    schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Frozen copy of the referenced `ConsentDocument`'s content at publish time (Task 073) -- no
    # foreign key here on purpose: editing/deleting the source document must never change what an
    # already-published version shows, exactly like `schema` above is a frozen copy, not a pointer.
    consent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_document_title: Mapped[str | None] = mapped_column(String(300))
    consent_document_body_html: Mapped[str | None] = mapped_column(Text)
    consent_checkbox_text: Mapped[str | None] = mapped_column(Text)

    # Frozen copy of the draft's attempt settings at publish time (Task 075).
    allow_retake: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_attempt_history: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_scores: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    definition: Mapped[TestDefinitionRecord] = relationship(
        back_populates="versions", foreign_keys=[test_definition_id]
    )


class TestAttemptRecord(Base, TimestampMixin):
    __tablename__ = "form_test_attempts"
    __table_args__ = (
        # Was a plain UniqueConstraint("user_id", "test_version_id") -- relaxed for retake
        # (Task 075) to "at most one *in-progress* attempt per user per version", so a retake can
        # create a second, independent `completed` row without disturbing the first.
        Index(
            "uq_form_test_attempts_user_version_in_progress",
            "user_id",
            "test_version_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    test_definition_id: Mapped[int] = mapped_column(
        ForeignKey("form_tests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    test_version_id: Mapped[int] = mapped_column(
        ForeignKey("form_test_versions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # CASCADE (not RESTRICT, unlike form_submissions before Task 064): deleting a user via the
    # consent sweep must erase their attempts for free -- see docs/tasks/068's "Domain owner and
    # dependencies".
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[TestAttemptStatus] = mapped_column(
        Enum(
            TestAttemptStatus,
            name="test_attempt_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TestAttemptStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    computed_results: Mapped[dict | None] = mapped_column(JSONB)
    rendered_result_text: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    consent_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identity_snapshot: Mapped[dict | None] = mapped_column(JSONB)


class ConsentDocumentRecord(Base, TimestampMixin):
    """Per-bot library of admin-authored consent documents (Task 073) -- freely created, edited,
    and deleted; not itself draft/version-tracked (see `ConsentDocument`'s docstring)."""

    __tablename__ = "form_test_consent_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
