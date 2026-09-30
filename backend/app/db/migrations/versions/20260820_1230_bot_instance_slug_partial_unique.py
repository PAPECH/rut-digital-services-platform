"""Allow a soft-deleted bot's slug to be reused by a new live bot.

Revision ID: 6f3d9a2c5e14
Revises: 9a1c3e5f7b02
Create Date: 2026-08-20 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6f3d9a2c5e14"
down_revision: str | None = "9a1c3e5f7b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_bot_instances_slug", table_name="bot_instances")
    op.create_index("ix_bot_instances_slug", "bot_instances", ["slug"], unique=False)
    op.create_index(
        "uq_bot_instances_slug_live",
        "bot_instances",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_bot_instances_slug_live", table_name="bot_instances")
    op.drop_index("ix_bot_instances_slug", table_name="bot_instances")
    op.create_index("ix_bot_instances_slug", "bot_instances", ["slug"], unique=True)
