"""Add form catalog visibility and explicitly shared drafts.

Revision ID: 4f31c8de9a72
Revises: 7ac31d4e1b20
Create Date: 2026-08-13 19:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f31c8de9a72"
down_revision: str | None = "7ac31d4e1b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "form_templates",
        sa.Column("show_in_catalog", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "form_drafts",
        sa.Column("is_shared", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "content_drafts",
        sa.Column("is_shared", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_form_drafts_is_shared", "form_drafts", ["is_shared"])
    op.create_index("ix_content_drafts_is_shared", "content_drafts", ["is_shared"])


def downgrade() -> None:
    op.drop_index("ix_content_drafts_is_shared", table_name="content_drafts")
    op.drop_index("ix_form_drafts_is_shared", table_name="form_drafts")
    op.drop_column("content_drafts", "is_shared")
    op.drop_column("form_drafts", "is_shared")
    op.drop_column("form_templates", "show_in_catalog")
