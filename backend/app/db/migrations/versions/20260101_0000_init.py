"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-01-01 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ENUM-типы создаются ОДНИН раз идемпотентно (DO-блок). Колонки используют ссылки
# на эти типы с create_type=False — иначе SQLAlchemy попытается создать тип повторно
# при создании каждой таблицы и упадёт с DuplicateObject.
system_enum = postgresql.ENUM("max", "beavers", name="system_enum", create_type=False)
admin_role_enum = postgresql.ENUM("employee", "admin", name="admin_role_enum", create_type=False)
field_type_enum = postgresql.ENUM(
    "string", "number", "date", "checkbox", name="field_type_enum", create_type=False
)
submission_status_enum = postgresql.ENUM(
    "new", "in_work", "rejected", "done", name="submission_status_enum", create_type=False
)
message_direction_enum = postgresql.ENUM("in", "out", name="message_direction_enum", create_type=False)


_ENUM_DEFS: list[tuple[str, tuple[str, ...]]] = [
    ("system_enum", ("max", "beavers")),
    ("admin_role_enum", ("employee", "admin")),
    ("field_type_enum", ("string", "number", "date", "checkbox")),
    ("submission_status_enum", ("new", "in_work", "rejected", "done")),
    ("message_direction_enum", ("in", "out")),
]


def _create_enum_idempotent(name: str, values: tuple[str, ...]) -> None:
    """CREATE TYPE ... AS ENUM(...) — идемпотентно через DO-блок."""
    quoted = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({quoted});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )


def upgrade() -> None:
    for name, values in _ENUM_DEFS:
        _create_enum_idempotent(name, values)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("system", system_enum, nullable=False),
        sa.Column("last_name", sa.String(120)),
        sa.Column("first_name", sa.String(120)),
        sa.Column("username", sa.String(120)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(180)),
        sa.Column("photo_url", sa.String(512)),
        sa.Column("language_code", sa.String(16), server_default="ru"),
        sa.Column("birth_date", sa.Date()),
        sa.Column("study_group", sa.String(64)),
        sa.Column("rut_personnel_number", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "system", name="uq_users_user_id_system"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"])
    op.create_index("ix_users_system", "users", ["system"])

    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("max_user_id", sa.String(64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", admin_role_enum, nullable=False, server_default="employee"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_admins_max_user_id", "admins", ["max_user_id"])

    op.create_table(
        "form_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "form_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "form_template_id",
            sa.Integer(),
            sa.ForeignKey("form_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("type", field_type_enum, nullable=False),
        sa.Column("regexp", sa.String(500)),
        sa.Column("min_value", sa.String(64)),
        sa.Column("max_value", sa.String(64)),
        sa.Column("default_value", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profile_key", sa.String(40)),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_form_fields_form_template_id", "form_fields", ["form_template_id"])

    op.create_table(
        "form_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "form_template_id",
            sa.Integer(),
            sa.ForeignKey("form_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("values_en", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("status", submission_status_enum, nullable=False, server_default="new"),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("assignee_admin_id", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("idempotency_key", sa.String(64), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_form_submissions_form_template_id", "form_submissions", ["form_template_id"])
    op.create_index("ix_form_submissions_user_id", "form_submissions", ["user_id"])
    op.create_index("ix_form_submissions_status", "form_submissions", ["status"])
    op.create_index("ix_form_submissions_idempotency_key", "form_submissions", ["idempotency_key"])

    op.create_table(
        "submission_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("form_submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", submission_status_enum),
        sa.Column("to_status", submission_status_enum, nullable=False),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.Text()),
    )
    op.create_index(
        "ix_submission_status_history_submission_id", "submission_status_history", ["submission_id"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("system", system_enum, nullable=False),
        sa.Column("direction", message_direction_enum, nullable=False),
        sa.Column("text", sa.Text()),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("is_ai_answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_classification", sa.String(120)),
        sa.Column("replied_by_admin_id", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("external_id", sa.String(120), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_system", "messages", ["system"])
    op.create_index("ix_messages_external_id", "messages", ["external_id"])

    op.create_table(
        "kb_faq",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("question_en", sa.String(500)),
        sa.Column("answer_en", sa.Text()),
        sa.Column("language", sa.String(16), server_default="ru"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "kb_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "monitoring_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("system", system_enum, nullable=False),
        sa.Column("request_number", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "request_number", name="uq_monitoring_user_request"),
    )
    op.create_index("ix_monitoring_subscriptions_user_id", "monitoring_subscriptions", ["user_id"])
    op.create_index("ix_monitoring_subscriptions_system", "monitoring_subscriptions", ["system"])
    op.create_index(
        "ix_monitoring_subscriptions_request_number", "monitoring_subscriptions", ["request_number"]
    )

    op.create_table(
        "monitoring_states",
        sa.Column("request_number", sa.String(64), primary_key=True),
        sa.Column("last_status", sa.String(200)),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("monitoring_states")
    op.drop_table("monitoring_subscriptions")
    op.drop_table("kb_documents")
    op.drop_table("kb_faq")
    op.drop_table("messages")
    op.drop_table("submission_status_history")
    op.drop_table("form_submissions")
    op.drop_table("form_fields")
    op.drop_table("form_templates")
    op.drop_table("admins")
    op.drop_table("users")

    for name, _ in reversed(_ENUM_DEFS):
        op.execute(f"DROP TYPE IF EXISTS {name}")
