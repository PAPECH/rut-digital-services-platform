"""Tenant admission-rating capability.

Revision ID: b95d20f6e301
Revises: a84c19e5d2f0
Create Date: 2026-08-12 00:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b95d20f6e301"
down_revision: str | None = "a84c19e5d2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.add_column(
        "push_outbox",
        sa.Column("bot_instance_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_push_outbox_bot_instance_id",
        "push_outbox",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        UPDATE push_outbox
        SET bot_instance_id = (
            SELECT id FROM bot_instances WHERE slug = 'default'
        )
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column("push_outbox", "bot_instance_id", nullable=False)
    op.create_index("ix_push_outbox_bot_instance_id", "push_outbox", ["bot_instance_id"])
    op.create_table(
        "admission_rating_plans",
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
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("specialty", sa.String(255), nullable=False),
        sa.Column("qualification", sa.String(64), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("bot_instance_id", "plan_id", name="uq_admission_rating_plan_bot_plan"),
    )
    op.create_index(
        "ix_admission_rating_plans_bot_instance_id", "admission_rating_plans", ["bot_instance_id"]
    )
    op.create_index(
        "ix_admission_rating_plans_installation_id", "admission_rating_plans", ["installation_id"]
    )
    op.create_table(
        "admission_rating_states",
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
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("applicant_code", sa.String(64), nullable=False),
        sa.Column("applicant_code_hash", sa.String(64), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("preference", sa.String(255), nullable=False),
        sa.Column("competition", sa.String(255), nullable=False),
        sa.Column("group_name", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "bot_instance_id",
            "plan_id",
            "applicant_code_hash",
            "competition",
            name="uq_admission_rating_state",
        ),
    )
    op.create_index(
        "ix_admission_rating_states_bot_instance_id", "admission_rating_states", ["bot_instance_id"]
    )
    op.create_index(
        "ix_admission_rating_states_installation_id", "admission_rating_states", ["installation_id"]
    )
    op.create_index(
        "ix_admission_rating_states_applicant_code_hash", "admission_rating_states", ["applicant_code_hash"]
    )
    op.create_table(
        "admission_rating_subscriptions",
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
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_code", sa.String(64), nullable=False),
        sa.Column("applicant_code_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint(
            "bot_instance_id", "user_id", "applicant_code_hash", name="uq_admission_rating_subscription"
        ),
    )
    for column in ("bot_instance_id", "installation_id", "user_id", "applicant_code_hash"):
        op.create_index(
            f"ix_admission_rating_subscriptions_{column}", "admission_rating_subscriptions", [column]
        )

    op.execute(
        """
        INSERT INTO capability_installations (
            bot_instance_id, capability_key, is_enabled, "order", config, config_revision,
            last_health_status, created_at, updated_at
        )
        SELECT bot.id, 'admission_rating', true, 1,
            jsonb_build_object(
                'provider', 'rut_admission', 'admission_year', EXTRACT(YEAR FROM now())::integer,
                'polling_interval_seconds', 900, 'notifications_enabled', true,
                'title', 'Место в рейтинге',
                'subtitle', 'Введите уникальный код поступающего.',
                'lookup_label', 'Уникальный код поступающего',
                'not_found_text', 'Записи в рейтинге не найдены.'
            ), 1, 'unknown', now(), now()
        FROM bot_instances AS bot WHERE bot.slug = 'default'
        ON CONFLICT (bot_instance_id, capability_key) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO admission_rating_plans (
            bot_instance_id, installation_id, plan_id, specialty, qualification, created_at, updated_at
        )
        SELECT installation.bot_instance_id, installation.id, plan.plan_id,
               plan.spec_display_name, plan.spec_qualifier, plan.created_at, plan.updated_at
        FROM admission_plans AS plan
        JOIN capability_installations AS installation ON installation.capability_key = 'admission_rating'
        JOIN bot_instances AS bot ON bot.id = installation.bot_instance_id AND bot.slug = 'default'
        ON CONFLICT (bot_instance_id, plan_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO admission_rating_states (
            bot_instance_id, installation_id, plan_id, applicant_code, applicant_code_hash,
            points, preference, competition, group_name, position, total, checked_at
        )
        SELECT installation.bot_instance_id, installation.id, state.plan_id,
               upper(regexp_replace(trim(state.display_name), '\\s+', '', 'g')),
               encode(digest(installation.bot_instance_id::text || ':' || upper(regexp_replace(trim(state.display_name), '\\s+', '', 'g')), 'sha256'), 'hex'),
               state.points, state.preference_index_display, state.competition_name,
               state.group_name, state.rating_index,
               CASE state.competition_name
                 WHEN 'ALL' THEN plan."all" WHEN 'BUDGET' THEN plan.budget
                 WHEN 'CONCOURSE' THEN plan.concourse WHEN 'SPECIAL_QUOTA' THEN plan.special_quota
                 WHEN 'TARGET_QUOTA' THEN plan.target_quota WHEN 'QUOTA_07' THEN plan.quota_07
                 WHEN 'PAID' THEN plan.paid ELSE 0 END,
               state.checked_at
        FROM rating_states AS state
        JOIN admission_plans AS plan ON plan.plan_id = state.plan_id
        JOIN capability_installations AS installation ON installation.capability_key = 'admission_rating'
        JOIN bot_instances AS bot ON bot.id = installation.bot_instance_id AND bot.slug = 'default'
        ON CONFLICT (bot_instance_id, plan_id, applicant_code_hash, competition) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO admission_rating_subscriptions (
            bot_instance_id, installation_id, user_id, applicant_code, applicant_code_hash,
            is_active, created_at, updated_at
        )
        SELECT installation.bot_instance_id, installation.id, subscription.user_id,
               upper(regexp_replace(trim(subscription.display_name), '\\s+', '', 'g')),
               encode(digest(installation.bot_instance_id::text || ':' || upper(regexp_replace(trim(subscription.display_name), '\\s+', '', 'g')), 'sha256'), 'hex'),
               subscription.is_active, subscription.created_at, subscription.updated_at
        FROM rating_subscriptions AS subscription
        JOIN capability_installations AS installation ON installation.capability_key = 'admission_rating'
        JOIN bot_instances AS bot ON bot.id = installation.bot_instance_id AND bot.slug = 'default'
        ON CONFLICT (bot_instance_id, user_id, applicant_code_hash) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM admission_rating_states AS state
            JOIN bot_instances AS bot ON bot.id = state.bot_instance_id
            WHERE bot.slug <> 'default'
          ) OR EXISTS (
            SELECT 1 FROM admission_rating_subscriptions AS subscription
            JOIN bot_instances AS bot ON bot.id = subscription.bot_instance_id
            WHERE bot.slug <> 'default'
          ) OR EXISTS (
            SELECT 1 FROM push_outbox AS push
            JOIN bot_instances AS bot ON bot.id = push.bot_instance_id
            WHERE bot.slug <> 'default'
          ) THEN
            RAISE EXCEPTION 'Cannot downgrade admission rating with non-default tenant data';
          END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1
            FROM admission_rating_plans AS new_plan
            JOIN bot_instances AS bot ON bot.id = new_plan.bot_instance_id
            LEFT JOIN admission_plans AS legacy_plan ON legacy_plan.plan_id = new_plan.plan_id
            WHERE bot.slug = 'default' AND legacy_plan.plan_id IS NULL
          ) THEN
            RAISE EXCEPTION 'Cannot downgrade admission rating with plans absent from legacy storage';
          END IF;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE admission_plans AS legacy
        SET spec_display_name = current.specialty,
            spec_qualifier = current.qualification,
            updated_at = current.updated_at
        FROM admission_rating_plans AS current
        JOIN bot_instances AS bot ON bot.id = current.bot_instance_id AND bot.slug = 'default'
        WHERE legacy.plan_id = current.plan_id
        """
    )
    op.execute("DELETE FROM rating_states")
    op.execute(
        """
        INSERT INTO rating_states (
            plan_id, display_name, competition_name, points,
            preference_index_display, group_name, rating_index, checked_at
        )
        SELECT state.plan_id, state.applicant_code, state.competition, state.points,
               state.preference, state.group_name, state.position, state.checked_at
        FROM admission_rating_states AS state
        JOIN bot_instances AS bot ON bot.id = state.bot_instance_id AND bot.slug = 'default'
        """
    )
    op.execute("DELETE FROM rating_subscriptions")
    op.execute(
        """
        INSERT INTO rating_subscriptions (
            user_id, display_name, is_active, created_at, updated_at
        )
        SELECT subscription.user_id, subscription.applicant_code, subscription.is_active,
               subscription.created_at, subscription.updated_at
        FROM admission_rating_subscriptions AS subscription
        JOIN bot_instances AS bot
          ON bot.id = subscription.bot_instance_id AND bot.slug = 'default'
        """
    )
    op.execute("DELETE FROM capability_installations WHERE capability_key = 'admission_rating'")
    op.drop_table("admission_rating_subscriptions")
    op.drop_table("admission_rating_states")
    op.drop_table("admission_rating_plans")
    op.drop_index("ix_push_outbox_bot_instance_id", table_name="push_outbox")
    op.drop_constraint("fk_push_outbox_bot_instance_id", "push_outbox", type_="foreignkey")
    op.drop_column("push_outbox", "bot_instance_id")
