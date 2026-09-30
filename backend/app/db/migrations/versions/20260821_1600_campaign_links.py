"""Campaign (UTM) links, QR codes, and bot/webapp deep-link open tracking (Task 026).

Revision ID: c2d4f6a8b0e1
Revises: 7a1c13d55e47
Create Date: 2026-08-21 16:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d4f6a8b0e1"
down_revision: str | None = "7a1c13d55e47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(512), nullable=False),
        sa.Column("campaign", sa.String(200), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("placement", sa.String(200), nullable=False),
        sa.Column("target", sa.String(20), nullable=False),
        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
        ),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_opened_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_links_bot_instance_id", "campaign_links", ["bot_instance_id"])
    op.create_index(
        "uq_campaign_links_bot_code_live",
        "campaign_links",
        ["bot_instance_id", "code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "campaign_link_opens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_link_id",
            sa.Integer(),
            sa.ForeignKey("campaign_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bot_membership_id",
            sa.Integer(),
            sa.ForeignKey("bot_memberships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_campaign_link_opens_bot_instance_id", "campaign_link_opens", ["bot_instance_id"]
    )
    op.create_index(
        "ix_campaign_link_opens_campaign_link_id", "campaign_link_opens", ["campaign_link_id"]
    )
    op.create_index(
        "ix_campaign_link_opens_bot_membership_id", "campaign_link_opens", ["bot_membership_id"]
    )

    op.add_column(
        "bot_memberships",
        sa.Column(
            "source_campaign_link_id",
            sa.Integer(),
            sa.ForeignKey("campaign_links.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "ix_bot_memberships_source_campaign_link_id",
        "bot_memberships",
        ["source_campaign_link_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bot_memberships_source_campaign_link_id", table_name="bot_memberships")
    op.drop_column("bot_memberships", "source_campaign_link_id")
    op.drop_index(
        "ix_campaign_link_opens_bot_membership_id", table_name="campaign_link_opens"
    )
    op.drop_index(
        "ix_campaign_link_opens_campaign_link_id", table_name="campaign_link_opens"
    )
    op.drop_index("ix_campaign_link_opens_bot_instance_id", table_name="campaign_link_opens")
    op.drop_table("campaign_link_opens")
    op.drop_index("uq_campaign_links_bot_code_live", table_name="campaign_links")
    op.drop_index("ix_campaign_links_bot_instance_id", table_name="campaign_links")
    op.drop_table("campaign_links")
