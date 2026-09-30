"""Soft-delete support for bot instances.

Revision ID: 9a1c3e5f7b02
Revises: b5a6618029ba
Create Date: 2026-08-20 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9a1c3e5f7b02"
down_revision: str | None = "b5a6618029ba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bot_instances",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bot_instances", "deleted_at")
