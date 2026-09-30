"""Scored test/questionnaire module: form_tests, form_test_drafts, form_test_versions,
form_test_attempts, plus the can_manage_form_tests staff permission flag (Task 068)

Revision ID: 8721935f5fb2
Revises: 86b090bc281d
Create Date: 2026-09-18 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8721935f5fb2"
down_revision: str | None = "86b090bc281d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_ENUM_NAME = "test_attempt_status_enum"
_STATUS_VALUES = ("in_progress", "completed")


def upgrade() -> None:
    op.add_column(
        "admin_bot_access",
        sa.Column("can_manage_form_tests", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("admin_bot_access", "can_manage_form_tests", server_default=None)

    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {_STATUS_ENUM_NAME} AS ENUM ({", ".join(f"'{v}'" for v in _STATUS_VALUES)});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    # postgresql.ENUM (dialect-specific), not the generic sa.Enum: sa.Enum(create_type=False)
    # does not reliably suppress the implicit CREATE TYPE that create_table's column DDL
    # emits when adapting a generic Enum to Postgres's native type, which duplicated the
    # CREATE TYPE already issued by the guarded DO $$ block above and broke this migration
    # on every database, fresh or not (found during Task 068 readiness verification).
    status_enum = postgresql.ENUM(*_STATUS_VALUES, name=_STATUS_ENUM_NAME, create_type=False)

    op.create_table(
        "form_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_version_id", sa.Integer(), nullable=True),
        sa.Column("last_published_revision", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bot_instance_id", "slug", name="uq_form_tests_bot_slug"),
    )
    op.create_index("ix_form_tests_bot_instance_id", "form_tests", ["bot_instance_id"])

    op.create_table(
        "form_test_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "test_definition_id",
            sa.Integer(),
            sa.ForeignKey("form_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("intro_text", sa.Text(), nullable=True),
        sa.Column("schema", postgresql.JSONB(), nullable=False),
        sa.Column(
            "published_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("test_definition_id", "version", name="uq_form_test_versions_definition_number"),
    )
    op.create_index("ix_form_test_versions_test_definition_id", "form_test_versions", ["test_definition_id"])

    op.create_foreign_key(
        "fk_form_tests_published_version",
        "form_tests",
        "form_test_versions",
        ["published_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "form_test_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "test_definition_id",
            sa.Integer(),
            sa.ForeignKey("form_tests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("intro_text", sa.Text(), nullable=True),
        sa.Column("schema", postgresql.JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_form_test_drafts_test_definition_id", "form_test_drafts", ["test_definition_id"], unique=True
    )

    op.create_table(
        "form_test_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_definition_id",
            sa.Integer(),
            sa.ForeignKey("form_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_version_id",
            sa.Integer(),
            sa.ForeignKey("form_test_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # CASCADE, not RESTRICT: deleting a user via the consent sweep (Task 064) must erase
        # their attempts for free, with no change to modules/consent (see Task 068).
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="in_progress"),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("computed_results", postgresql.JSONB(), nullable=True),
        sa.Column("rendered_result_text", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "test_version_id", name="uq_form_test_attempts_user_version"),
    )
    op.create_index("ix_form_test_attempts_bot_instance_id", "form_test_attempts", ["bot_instance_id"])
    op.create_index("ix_form_test_attempts_test_definition_id", "form_test_attempts", ["test_definition_id"])
    op.create_index("ix_form_test_attempts_test_version_id", "form_test_attempts", ["test_version_id"])
    op.create_index("ix_form_test_attempts_user_id", "form_test_attempts", ["user_id"])
    op.create_index("ix_form_test_attempts_status", "form_test_attempts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_form_test_attempts_status", table_name="form_test_attempts")
    op.drop_index("ix_form_test_attempts_user_id", table_name="form_test_attempts")
    op.drop_index("ix_form_test_attempts_test_version_id", table_name="form_test_attempts")
    op.drop_index("ix_form_test_attempts_test_definition_id", table_name="form_test_attempts")
    op.drop_index("ix_form_test_attempts_bot_instance_id", table_name="form_test_attempts")
    op.drop_table("form_test_attempts")

    op.drop_index("ix_form_test_drafts_test_definition_id", table_name="form_test_drafts")
    op.drop_table("form_test_drafts")

    op.drop_constraint("fk_form_tests_published_version", "form_tests", type_="foreignkey")

    op.drop_index("ix_form_test_versions_test_definition_id", table_name="form_test_versions")
    op.drop_table("form_test_versions")

    op.drop_index("ix_form_tests_bot_instance_id", table_name="form_tests")
    op.drop_table("form_tests")

    op.execute(f"DROP TYPE IF EXISTS {_STATUS_ENUM_NAME}")

    op.drop_column("admin_bot_access", "can_manage_form_tests")
