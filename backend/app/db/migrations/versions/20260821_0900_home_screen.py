"""Configurable home screen: reserved singleton category per bot (Task 023).

Revision ID: 8c25e0f4b913
Revises: 6f3d9a2c5e14
Create Date: 2026-08-21 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c25e0f4b913"
down_revision: str | None = "6f3d9a2c5e14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "content_categories",
        sa.Column("is_home", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "uq_content_categories_home_per_bot",
        "content_categories",
        ["bot_instance_id"],
        unique=True,
        postgresql_where=sa.text("is_home"),
    )
    op.add_column(
        "content_drafts",
        sa.Column("header_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "content_versions",
        sa.Column("header_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("content_versions", "header_visible")
    op.drop_column("content_drafts", "header_visible")
    op.drop_index("uq_content_categories_home_per_bot", table_name="content_categories")
    op.drop_column("content_categories", "is_home")
