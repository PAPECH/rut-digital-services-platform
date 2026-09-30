"""Capability shortcut categories (Task 044).

Revision ID: 3c9a1f6b7d02
Revises: 0e50c9857148
Create Date: 2026-09-02 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c9a1f6b7d02"
down_revision: str | None = "0e50c9857148"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_categories", sa.Column("capability_key", sa.String(length=64), nullable=True))
    op.add_column("content_categories", sa.Column("capability_view_key", sa.String(length=64), nullable=True))
    op.add_column("content_categories", sa.Column("title", sa.String(length=300), nullable=True))
    op.add_column("content_categories", sa.Column("subtitle", sa.Text(), nullable=True))
    op.add_column("content_categories", sa.Column("image_url", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_content_category_capability_pair",
        "content_categories",
        "(capability_key IS NULL) = (capability_view_key IS NULL)",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM content_categories WHERE capability_key IS NOT NULL
          ) THEN
            RAISE EXCEPTION 'Cannot downgrade: capability shortcut rows exist';
          END IF;
        END $$;
        """
    )
    op.drop_constraint("ck_content_category_capability_pair", "content_categories", type_="check")
    op.drop_column("content_categories", "image_url")
    op.drop_column("content_categories", "subtitle")
    op.drop_column("content_categories", "title")
    op.drop_column("content_categories", "capability_view_key")
    op.drop_column("content_categories", "capability_key")
