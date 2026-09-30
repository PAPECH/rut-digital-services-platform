"""Add tenant-scoped parent relationships to content categories.

Revision ID: 7ac31d4e1b20
Revises: f24b8d0ac731
Create Date: 2026-08-13 18:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7ac31d4e1b20"
down_revision: str | None = "f24b8d0ac731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_categories", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_content_category_parent",
        "content_categories",
        "content_categories",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_content_categories_parent_id", "content_categories", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_content_categories_parent_id", table_name="content_categories")
    op.drop_constraint("fk_content_category_parent", "content_categories", type_="foreignkey")
    op.drop_column("content_categories", "parent_id")
