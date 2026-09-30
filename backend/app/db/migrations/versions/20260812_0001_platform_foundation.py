"""Universal multi-bot platform foundation.

Revision ID: 8f41d2c9a601
Revises: 4e79ac7db8b7
Create Date: 2026-08-12 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8f41d2c9a601"
down_revision: str | None = "4e79ac7db8b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def upgrade() -> None:
    op.execute("ALTER TYPE admin_role_enum ADD VALUE IF NOT EXISTS 'platform_admin'")

    op.create_table(
        "bot_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "branding",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "profile_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        *_timestamps(),
    )
    op.create_index("ix_bot_instances_slug", "bot_instances", ["slug"], unique=True)
    op.execute(
        """
        INSERT INTO bot_instances (
            slug, name, description, branding, settings, profile_schema,
            is_active, "order", created_at, updated_at
        ) VALUES (
            'default',
            'Основной бот',
            'Экземпляр, созданный при переходе на универсальную платформу',
            '{}'::jsonb,
            '{}'::jsonb,
            jsonb_build_array(
              jsonb_build_object('key', 'last_name', 'label', 'Фамилия', 'type', 'string', 'required', true, 'shared', true),
              jsonb_build_object('key', 'first_name', 'label', 'Имя', 'type', 'string', 'required', true, 'shared', true),
              jsonb_build_object('key', 'patronymic', 'label', 'Отчество', 'type', 'string', 'required', true, 'shared', true),
              jsonb_build_object('key', 'phone', 'label', 'Телефон', 'type', 'phone', 'required', true, 'shared', true),
              jsonb_build_object('key', 'phone_verified', 'label', 'Подтверждённый телефон', 'type', 'boolean', 'required', true, 'shared', true),
              jsonb_build_object('key', 'job_title', 'label', 'Должность', 'type', 'string', 'required', true, 'shared', true),
              jsonb_build_object('key', 'structural_unit', 'label', 'Структурное подразделение', 'type', 'string', 'required', true, 'shared', true)
            ),
            true, 0, now(), now()
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )

    op.create_table(
        "admin_bot_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("can_process_submissions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("can_manage_content", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_manage_forms", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_manage_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_manage_maintenance", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
        sa.UniqueConstraint("admin_id", "bot_instance_id", name="uq_admin_bot_access"),
    )
    op.create_index("ix_admin_bot_access_admin_id", "admin_bot_access", ["admin_id"])
    op.create_index("ix_admin_bot_access_bot_instance_id", "admin_bot_access", ["bot_instance_id"])

    op.create_table(
        "bot_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "local_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ban_chat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_chat_reason", sa.Text()),
        sa.Column("ban_forms", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_forms_reason", sa.Text()),
        sa.Column("ban_app", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_app_reason", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("bot_instance_id", "user_id", name="uq_bot_membership_bot_user"),
    )
    op.create_index("ix_bot_memberships_bot_instance_id", "bot_memberships", ["bot_instance_id"])
    op.create_index("ix_bot_memberships_user_id", "bot_memberships", ["user_id"])

    op.create_table(
        "maintenance_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_key", sa.String(100), nullable=False),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
        ),
        sa.Column("mode", sa.String(32), nullable=False, server_default="off"),
        sa.Column("title", sa.String(240), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("retry_after_seconds", sa.Integer()),
        sa.Column("allow_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        *_timestamps(),
    )
    op.create_index("ix_maintenance_policies_scope_key", "maintenance_policies", ["scope_key"], unique=True)
    op.create_index(
        "ix_maintenance_policies_bot_instance_id",
        "maintenance_policies",
        ["bot_instance_id"],
    )

    op.create_table(
        "admin_refresh_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "replaced_by_id",
            sa.Integer(),
            sa.ForeignKey("admin_refresh_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip", sa.String(64)),
    )
    op.create_index("ix_admin_refresh_sessions_admin_id", "admin_refresh_sessions", ["admin_id"])
    op.create_index("ix_admin_refresh_sessions_family_id", "admin_refresh_sessions", ["family_id"])
    op.create_index(
        "ix_admin_refresh_sessions_token_hash",
        "admin_refresh_sessions",
        ["token_hash"],
        unique=True,
    )

    op.add_column("users", sa.Column("job_title", sa.String(240)))
    op.add_column("users", sa.Column("structural_unit", sa.String(500)))
    op.add_column(
        "users",
        sa.Column(
            "shared_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column("form_templates", sa.Column("bot_instance_id", sa.Integer()))
    op.add_column("form_submissions", sa.Column("bot_instance_id", sa.Integer()))
    op.execute(
        """
        UPDATE form_templates
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE form_submissions
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column("form_templates", "bot_instance_id", nullable=False)
    op.alter_column("form_submissions", "bot_instance_id", nullable=False)
    op.create_foreign_key(
        "fk_form_templates_bot_instance_id",
        "form_templates",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_form_submissions_bot_instance_id",
        "form_submissions",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_form_templates_bot_instance_id", "form_templates", ["bot_instance_id"])
    op.create_index("ix_form_submissions_bot_instance_id", "form_submissions", ["bot_instance_id"])

    op.drop_index("ix_form_submissions_idempotency_key", table_name="form_submissions")
    op.create_index(
        "ix_form_submissions_idempotency_key",
        "form_submissions",
        ["idempotency_key"],
    )
    op.create_unique_constraint(
        "uq_form_submission_bot_idempotency",
        "form_submissions",
        ["bot_instance_id", "idempotency_key"],
    )

    op.execute(
        """
        INSERT INTO admin_bot_access (
            admin_id, bot_instance_id, can_process_submissions,
            can_manage_content, can_manage_forms, can_manage_staff,
            can_manage_maintenance, created_at, updated_at
        )
        SELECT
            admins.id,
            bot_instances.id,
            true,
            admins.role::text = 'admin',
            admins.role::text = 'admin',
            admins.role::text = 'admin',
            admins.role::text = 'admin',
            now(),
            now()
        FROM admins
        CROSS JOIN bot_instances
        WHERE bot_instances.slug = 'default'
        ON CONFLICT (admin_id, bot_instance_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO bot_memberships (
            bot_instance_id, user_id, is_active, local_data,
            ban_chat, ban_chat_reason, ban_forms, ban_forms_reason,
            ban_app, ban_app_reason, created_at, updated_at
        )
        SELECT
            bot_instances.id,
            users.id,
            true,
            '{}'::jsonb,
            users.ban_chat,
            users.ban_chat_reason,
            users.ban_forms,
            users.ban_forms_reason,
            users.ban_app,
            users.ban_app_reason,
            now(),
            now()
        FROM users
        CROSS JOIN bot_instances
        WHERE bot_instances.slug = 'default'
        ON CONFLICT (bot_instance_id, user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_constraint("uq_form_submission_bot_idempotency", "form_submissions", type_="unique")
    op.drop_index("ix_form_submissions_idempotency_key", table_name="form_submissions")
    op.create_index(
        "ix_form_submissions_idempotency_key",
        "form_submissions",
        ["idempotency_key"],
        unique=True,
    )

    op.drop_index("ix_form_submissions_bot_instance_id", table_name="form_submissions")
    op.drop_index("ix_form_templates_bot_instance_id", table_name="form_templates")
    op.drop_constraint("fk_form_submissions_bot_instance_id", "form_submissions", type_="foreignkey")
    op.drop_constraint("fk_form_templates_bot_instance_id", "form_templates", type_="foreignkey")
    op.drop_column("form_submissions", "bot_instance_id")
    op.drop_column("form_templates", "bot_instance_id")

    op.drop_column("users", "shared_data")
    op.drop_column("users", "structural_unit")
    op.drop_column("users", "job_title")

    op.drop_table("admin_refresh_sessions")
    op.drop_table("maintenance_policies")
    op.drop_table("bot_memberships")
    op.drop_table("admin_bot_access")
    op.drop_table("bot_instances")

    # PostgreSQL cannot safely remove one enum value while dependent columns exist.
    # Keeping the unused value makes downgrade data-safe and does not affect old code.
