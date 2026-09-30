"""Add typed and idempotent analytics event dimensions.

Revision ID: 8e2c7a1d4f90
Revises: 1b7d5e2a9c40
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "8e2c7a1d4f90"
down_revision: str | None = "1b7d5e2a9c40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("event_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("source_surface", sa.String(length=32), nullable=True),
        sa.Column("interaction_kind", sa.String(length=64), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("source_category_id", sa.Integer(), nullable=True),
        sa.Column("content_version_id", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.String(length=64), nullable=True),
        sa.Column("item_id", sa.String(length=64), nullable=True),
        sa.Column("tabs_block_id", sa.String(length=64), nullable=True),
        sa.Column("tab_key", sa.String(length=64), nullable=True),
        sa.Column("form_template_id", sa.Integer(), nullable=True),
        sa.Column("form_version_id", sa.Integer(), nullable=True),
        sa.Column("faq_id", sa.Integer(), nullable=True),
        sa.Column("attachment_id", sa.Integer(), nullable=True),
        sa.Column("capability_installation_id", sa.Integer(), nullable=True),
        sa.Column("capability_key", sa.String(length=64), nullable=True),
        sa.Column("capability_view_key", sa.String(length=64), nullable=True),
        sa.Column("outcome_code", sa.String(length=64), nullable=True),
    )
    for column in columns:
        op.add_column("user_actions", column)

    # Deterministic UUIDs make the migration replayable without requiring a DB extension.
    op.execute(
        """
        UPDATE user_actions
        SET event_id = (
            substr(md5('user_action:' || id::text), 1, 8) || '-' ||
            substr(md5('user_action:' || id::text), 9, 4) || '-' ||
            substr(md5('user_action:' || id::text), 13, 4) || '-' ||
            substr(md5('user_action:' || id::text), 17, 4) || '-' ||
            substr(md5('user_action:' || id::text), 21, 12)
        )
        """
    )
    op.execute(
        """
        UPDATE user_actions
        SET
            category_id = CASE
                WHEN payload->>'category_id' ~ '^[0-9]+$' THEN (payload->>'category_id')::integer
                ELSE NULL
            END,
            content_version_id = CASE
                WHEN payload->>'version_id' ~ '^[0-9]+$' THEN (payload->>'version_id')::integer
                ELSE NULL
            END,
            form_template_id = CASE
                WHEN payload->>'form_id' ~ '^[0-9]+$' THEN (payload->>'form_id')::integer
                ELSE NULL
            END,
            form_version_id = CASE
                WHEN payload->>'form_version_id' ~ '^[0-9]+$' THEN (payload->>'form_version_id')::integer
                ELSE NULL
            END,
            capability_installation_id = CASE
                WHEN payload->>'installation_id' ~ '^[0-9]+$' THEN (payload->>'installation_id')::integer
                ELSE NULL
            END,
            capability_key = NULLIF(payload->>'capability_key', ''),
            capability_view_key = NULLIF(payload->>'view_key', ''),
            tab_key = NULLIF(payload->>'tab_key', ''),
            outcome_code = COALESCE(
                NULLIF(payload->>'outcome', ''),
                CASE
                    WHEN payload::jsonb ? 'enabled' THEN
                        CASE WHEN (payload->>'enabled')::boolean THEN 'enabled' ELSE 'disabled' END
                    ELSE NULL
                END
            ),
            source_surface = 'legacy'
        WHERE payload IS NOT NULL
        """
    )

    op.alter_column("user_actions", "event_id", existing_type=sa.String(length=36), nullable=False)
    op.create_unique_constraint("uq_user_actions_event_id", "user_actions", ["event_id"])
    op.create_index(
        "ix_user_actions_bot_created", "user_actions", ["bot_instance_id", "created_at"]
    )
    op.create_index("ix_user_actions_type_created", "user_actions", ["action_type", "created_at"])
    op.create_index(
        "ix_user_actions_user_bot_created",
        "user_actions",
        ["user_id", "bot_instance_id", "created_at"],
    )
    op.create_index("ix_user_actions_category_created", "user_actions", ["category_id", "created_at"])
    op.create_index("ix_user_actions_form_created", "user_actions", ["form_template_id", "created_at"])
    op.create_index(
        "ix_user_actions_capability_created", "user_actions", ["capability_key", "created_at"]
    )


def downgrade() -> None:
    for name in (
        "ix_user_actions_capability_created",
        "ix_user_actions_form_created",
        "ix_user_actions_category_created",
        "ix_user_actions_user_bot_created",
        "ix_user_actions_type_created",
        "ix_user_actions_bot_created",
    ):
        op.drop_index(name, table_name="user_actions")
    op.drop_constraint("uq_user_actions_event_id", "user_actions", type_="unique")
    for name in (
        "outcome_code",
        "capability_view_key",
        "capability_key",
        "capability_installation_id",
        "attachment_id",
        "faq_id",
        "form_version_id",
        "form_template_id",
        "tab_key",
        "tabs_block_id",
        "item_id",
        "block_id",
        "content_version_id",
        "source_category_id",
        "category_id",
        "interaction_kind",
        "source_surface",
        "session_id",
        "event_id",
    ):
        op.drop_column("user_actions", name)
