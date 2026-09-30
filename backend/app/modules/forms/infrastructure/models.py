from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....db.base import Base, TimestampMixin
from ....models.enums import FieldTypeEnum, SubmissionStatusEnum


class FormDefinitionRecord(Base, TimestampMixin):
    __tablename__ = "form_templates"
    __table_args__ = (UniqueConstraint("bot_instance_id", "slug", name="uq_form_template_bot_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "form_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_form_template_published_version",
        )
    )
    last_published_revision: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)

    # Legacy display columns remain during the additive migration and rollback window.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_in_catalog: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_on_accept: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    fields: Mapped[list[LegacyFormFieldRecord]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="LegacyFormFieldRecord.order",
    )
    draft: Mapped[FormDraftRecord | None] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="FormDraftRecord.form_definition_id",
    )
    versions: Mapped[list[FormVersionRecord]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        foreign_keys="FormVersionRecord.form_definition_id",
        order_by="FormVersionRecord.version",
    )


class LegacyFormFieldRecord(Base, TimestampMixin):
    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    form_template_id: Mapped[int] = mapped_column(
        ForeignKey("form_templates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[FieldTypeEnum] = mapped_column(Enum(FieldTypeEnum, name="field_type_enum"), nullable=False)
    regexp: Mapped[str | None] = mapped_column(String(500))
    min_value: Mapped[str | None] = mapped_column(String(64))
    max_value: Mapped[str | None] = mapped_column(String(64))
    default_value: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_key: Mapped[str | None] = mapped_column(String(40))
    meta: Mapped[dict | None] = mapped_column(JSONB)

    template: Mapped[FormDefinitionRecord] = relationship(back_populates="fields")


class FormDraftRecord(Base, TimestampMixin):
    __tablename__ = "form_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    form_definition_id: Mapped[int] = mapped_column(
        ForeignKey("form_templates.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reply_on_accept: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    definition: Mapped[FormDefinitionRecord] = relationship(
        back_populates="draft", foreign_keys=[form_definition_id]
    )


class FormVersionRecord(Base):
    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("form_definition_id", "version", name="uq_form_version_definition_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    form_definition_id: Mapped[int] = mapped_column(
        ForeignKey("form_templates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reply_on_accept: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSONB, nullable=False)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    definition: Mapped[FormDefinitionRecord] = relationship(
        back_populates="versions", foreign_keys=[form_definition_id]
    )


class FormSubmission(Base, TimestampMixin):
    __tablename__ = "form_submissions"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "idempotency_key",
            name="uq_form_submission_bot_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    form_template_id: Mapped[int] = mapped_column(
        ForeignKey("form_templates.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    form_version_id: Mapped[int] = mapped_column(
        ForeignKey("form_versions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    values: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    values_en: Mapped[dict | None] = mapped_column(JSONB)

    field_labels: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    form_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    profile_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[SubmissionStatusEnum] = mapped_column(
        Enum(SubmissionStatusEnum, name="submission_status_enum"),
        default=SubmissionStatusEnum.new,
        nullable=False,
        index=True,
    )

    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))

    idempotency_key: Mapped[str | None] = mapped_column(String(64), index=True)

    history: Mapped[list[SubmissionStatusHistory]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionStatusHistory.changed_at",
    )
    appointment_slots: Mapped[list[SubmissionAppointmentSlot]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionAppointmentSlot.starts_at",
    )


class SubmissionStatusHistory(Base):
    __tablename__ = "submission_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("form_submissions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_status: Mapped[SubmissionStatusEnum | None] = mapped_column(
        Enum(SubmissionStatusEnum, name="submission_status_enum")
    )
    to_status: Mapped[SubmissionStatusEnum] = mapped_column(
        Enum(SubmissionStatusEnum, name="submission_status_enum"), nullable=False
    )
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    submission: Mapped[FormSubmission] = relationship(back_populates="history")


class SubmissionAppointmentSlot(Base):
    """One reserved 15-minute rector appointment slot.

    Storing a long appointment as one or two individual rows lets PostgreSQL's
    unique constraint prevent double booking even when two administrators save
    at the same time.
    """

    __tablename__ = "submission_appointment_slots"
    __table_args__ = (
        UniqueConstraint(
            "bot_instance_id",
            "starts_at",
            name="uq_submission_appointment_slot_bot_start",
        ),
        UniqueConstraint(
            "submission_id",
            "starts_at",
            name="uq_submission_appointment_slot_submission_start",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("form_submissions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    submission: Mapped[FormSubmission] = relationship(back_populates="appointment_slots")
