"""news_items table + user_actions.news_id (Task 040 - tenant news feed)

Revision ID: da7f87e5405a
Revises: 9b4e1f7a2c53
Create Date: 2026-08-27 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "da7f87e5405a"
down_revision: str | None = "9b4e1f7a2c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("title_en", sa.String(length=300), nullable=True),
        sa.Column("body_blocks", postgresql.JSONB(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column(
            "cover_attachment_id",
            sa.Integer(),
            sa.ForeignKey("attachments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_news_items_bot_instance_id", "news_items", ["bot_instance_id"]
    )
    op.create_index(
        "ix_news_items_bot_published", "news_items", ["bot_instance_id", "published_at", "id"]
    )
    op.add_column("user_actions", sa.Column("news_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_actions", "news_id")
    op.drop_index("ix_news_items_bot_published", table_name="news_items")
    op.drop_index("ix_news_items_bot_instance_id", table_name="news_items")
    op.drop_table("news_items")
