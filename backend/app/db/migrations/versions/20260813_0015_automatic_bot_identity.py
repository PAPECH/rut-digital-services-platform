"""Replace expected username with the actual MAX bot identity.

Revision ID: 1b7d5e2a9c40
Revises: 4f31c8de9a72
Create Date: 2026-08-13 21:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1b7d5e2a9c40"
down_revision: str | None = "4f31c8de9a72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("bot_runtimes", "expected_username")
    op.alter_column(
        "bot_runtimes",
        "connected_username",
        new_column_name="username",
        existing_type=sa.String(length=120),
    )
    op.alter_column(
        "bot_runtimes",
        "connected_user_id",
        new_column_name="max_bot_id",
        existing_type=sa.String(length=120),
    )


def downgrade() -> None:
    op.alter_column(
        "bot_runtimes",
        "max_bot_id",
        new_column_name="connected_user_id",
        existing_type=sa.String(length=120),
    )
    op.alter_column(
        "bot_runtimes",
        "username",
        new_column_name="connected_username",
        existing_type=sa.String(length=120),
    )
    op.add_column(
        "bot_runtimes",
        sa.Column("expected_username", sa.String(length=120), nullable=True),
    )
    op.execute(
        "UPDATE bot_runtimes SET expected_username = connected_username "
        "WHERE connected_username IS NOT NULL"
    )
