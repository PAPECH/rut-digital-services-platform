"""Dedicated `can_manage_campaigns` staff-access flag for campaign links (Task 026), replacing
the initial reuse of `can_manage_content` for this permission check.

Revision ID: d3e5a7c9b1f2
Revises: c2d4f6a8b0e1
Create Date: 2026-08-21 17:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e5a7c9b1f2"
down_revision: str | None = "c2d4f6a8b0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_bot_access",
        sa.Column(
            "can_manage_campaigns",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_bot_access", "can_manage_campaigns")
