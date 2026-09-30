"""Tenant capability registry and request-status capability.

Revision ID: a84c19e5d2f0
Revises: f7d9b3a64c12
Create Date: 2026-08-12 00:04:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a84c19e5d2f0"
down_revision: str | None = "f7d9b3a64c12"
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
    op.add_column(
        "admin_bot_access",
        sa.Column(
            "can_manage_capabilities",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "capability_installations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("capability_key", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("config_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("configured_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("enabled_by", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column(
            "last_health_status",
            sa.String(24),
            nullable=False,
            server_default="unconfigured",
        ),
        sa.Column("last_health_at", sa.DateTime(timezone=True)),
        sa.Column("last_health_error_code", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint(
            "bot_instance_id",
            "capability_key",
            name="uq_capability_installation_bot_key",
        ),
    )
    op.create_index(
        "ix_capability_installations_bot_instance_id",
        "capability_installations",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_capability_installations_capability_key",
        "capability_installations",
        ["capability_key"],
    )
    op.create_table(
        "request_status_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id",
            sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_number", sa.String(64), nullable=False),
        sa.Column("request_number_hash", sa.String(64), nullable=False),
        sa.Column("last_status", sa.Text()),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
        sa.UniqueConstraint(
            "bot_instance_id",
            "request_number_hash",
            name="uq_request_status_state_bot_hash",
        ),
    )
    op.create_index(
        "ix_request_status_states_bot_instance_id",
        "request_status_states",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_request_status_states_installation_id",
        "request_status_states",
        ["installation_id"],
    )
    op.create_index(
        "ix_request_status_states_request_number_hash",
        "request_status_states",
        ["request_number_hash"],
    )
    op.create_table(
        "request_status_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id",
            sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_number", sa.String(64), nullable=False),
        sa.Column("request_number_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint(
            "bot_instance_id",
            "user_id",
            "request_number_hash",
            name="uq_request_status_subscription_owner_hash",
        ),
    )
    op.create_index(
        "ix_request_status_subscriptions_bot_instance_id",
        "request_status_subscriptions",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_request_status_subscriptions_installation_id",
        "request_status_subscriptions",
        ["installation_id"],
    )
    op.create_index(
        "ix_request_status_subscriptions_user_id",
        "request_status_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "ix_request_status_subscriptions_request_number_hash",
        "request_status_subscriptions",
        ["request_number_hash"],
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO capability_installations (
            bot_instance_id, capability_key, is_enabled, "order", config,
            config_revision, last_health_status, created_at, updated_at
        )
        SELECT
            bot.id,
            'request_status',
            true,
            0,
            jsonb_build_object(
                'provider', 'google_sheets',
                'credential_ref', 'legacy_google_sheets',
                'spreadsheet_id', 'legacy',
                'sheet_range', 'B:C',
                'request_number_column', 0,
                'status_column', 1,
                'normalization', 'trim',
                'polling_interval_seconds', 300,
                'notifications_enabled', true,
                'title', 'Проверить статус заявления',
                'subtitle', 'Введите номер заявления, чтобы узнать актуальный статус.',
                'lookup_label', 'Номер заявления',
                'not_found_text', 'Заявление с таким номером не найдено.'
            ),
            1,
            'unknown',
            now(),
            now()
        FROM bot_instances AS bot
        WHERE bot.slug = 'default'
        ON CONFLICT (bot_instance_id, capability_key) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO request_status_states (
            bot_instance_id, installation_id, request_number,
            request_number_hash, last_status, checked_at, source_revision,
            created_at, updated_at
        )
        SELECT
            installation.bot_instance_id,
            installation.id,
            state.request_number,
            encode(
                digest(
                    installation.bot_instance_id::text || ':' || trim(state.request_number),
                    'sha256'
                ),
                'hex'
            ),
            state.last_status,
            state.checked_at,
            0,
            now(),
            now()
        FROM monitoring_states AS state
        JOIN capability_installations AS installation
          ON installation.capability_key = 'request_status'
        JOIN bot_instances AS bot
          ON bot.id = installation.bot_instance_id AND bot.slug = 'default'
        ON CONFLICT (bot_instance_id, request_number_hash) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO request_status_subscriptions (
            bot_instance_id, installation_id, user_id, request_number,
            request_number_hash, is_active, created_at, updated_at
        )
        SELECT
            installation.bot_instance_id,
            installation.id,
            subscription.user_id,
            subscription.request_number,
            encode(
                digest(
                    installation.bot_instance_id::text || ':' || trim(subscription.request_number),
                    'sha256'
                ),
                'hex'
            ),
            subscription.is_active,
            subscription.created_at,
            subscription.updated_at
        FROM monitoring_subscriptions AS subscription
        JOIN capability_installations AS installation
          ON installation.capability_key = 'request_status'
        JOIN bot_instances AS bot
          ON bot.id = installation.bot_instance_id AND bot.slug = 'default'
        ON CONFLICT (bot_instance_id, user_id, request_number_hash) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM request_status_subscriptions AS subscription
                JOIN bot_instances AS bot ON bot.id = subscription.bot_instance_id
                WHERE bot.slug <> 'default'
            ) OR EXISTS (
                SELECT 1
                FROM request_status_states AS state
                JOIN bot_instances AS bot ON bot.id = state.bot_instance_id
                WHERE bot.slug <> 'default'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: request-status contains multi-tenant data';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        INSERT INTO monitoring_states (request_number, last_status, checked_at)
        SELECT state.request_number, state.last_status, state.checked_at
        FROM request_status_states AS state
        JOIN bot_instances AS bot ON bot.id = state.bot_instance_id
        WHERE bot.slug = 'default'
        ON CONFLICT (request_number) DO UPDATE SET
            last_status = EXCLUDED.last_status,
            checked_at = EXCLUDED.checked_at
        """
    )
    op.execute(
        """
        INSERT INTO monitoring_subscriptions (
            user_id, system, request_number, is_active, created_at, updated_at
        )
        SELECT
            subscription.user_id,
            user_record.system,
            subscription.request_number,
            subscription.is_active,
            subscription.created_at,
            subscription.updated_at
        FROM request_status_subscriptions AS subscription
        JOIN bot_instances AS bot ON bot.id = subscription.bot_instance_id
        JOIN users AS user_record ON user_record.id = subscription.user_id
        WHERE bot.slug = 'default'
        ON CONFLICT (user_id, request_number) DO UPDATE SET
            is_active = EXCLUDED.is_active,
            updated_at = EXCLUDED.updated_at
        """
    )
    op.drop_index(
        "ix_request_status_subscriptions_request_number_hash",
        table_name="request_status_subscriptions",
    )
    op.drop_index(
        "ix_request_status_subscriptions_user_id",
        table_name="request_status_subscriptions",
    )
    op.drop_index(
        "ix_request_status_subscriptions_installation_id",
        table_name="request_status_subscriptions",
    )
    op.drop_index(
        "ix_request_status_subscriptions_bot_instance_id",
        table_name="request_status_subscriptions",
    )
    op.drop_table("request_status_subscriptions")
    op.drop_index(
        "ix_request_status_states_request_number_hash",
        table_name="request_status_states",
    )
    op.drop_index(
        "ix_request_status_states_installation_id",
        table_name="request_status_states",
    )
    op.drop_index(
        "ix_request_status_states_bot_instance_id",
        table_name="request_status_states",
    )
    op.drop_table("request_status_states")
    op.drop_index(
        "ix_capability_installations_capability_key",
        table_name="capability_installations",
    )
    op.drop_index(
        "ix_capability_installations_bot_instance_id",
        table_name="capability_installations",
    )
    op.drop_table("capability_installations")
    op.drop_column("admin_bot_access", "can_manage_capabilities")
