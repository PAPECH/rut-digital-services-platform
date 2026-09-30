"""Campaign-link repeat-open counter and unmatched-code capture (Task 074)

Revision ID: 7e2b4a9c1f38
Revises: 5c8e0f3a9d21
Create Date: 2026-09-22 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7e2b4a9c1f38"
down_revision: str | None = "5c8e0f3a9d21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "campaign_links",
        sa.Column("repeat_open_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("campaign_links", "repeat_open_count", server_default=None)

    op.create_table(
        "campaign_link_unmatched_opens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(512), nullable=False),
        sa.Column("event_source", sa.String(20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_campaign_link_unmatched_opens_bot_instance_id",
        "campaign_link_unmatched_opens",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_campaign_link_unmatched_opens_bot_code",
        "campaign_link_unmatched_opens",
        ["bot_instance_id", "code"],
    )
    op.create_index(
        "ix_campaign_link_unmatched_opens_bot_occurred",
        "campaign_link_unmatched_opens",
        ["bot_instance_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_link_unmatched_opens_bot_occurred",
        table_name="campaign_link_unmatched_opens",
    )
    op.drop_index(
        "ix_campaign_link_unmatched_opens_bot_code", table_name="campaign_link_unmatched_opens"
    )
    op.drop_index(
        "ix_campaign_link_unmatched_opens_bot_instance_id",
        table_name="campaign_link_unmatched_opens",
    )
    op.drop_table("campaign_link_unmatched_opens")

    op.drop_column("campaign_links", "repeat_open_count")
