"""Per-tenant bot runtime binding and heartbeat.

Revision ID: c92df1a4e870
Revises: f84abe5cad39
Create Date: 2026-08-12 23:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c92df1a4e870"
down_revision: str | None = "f84abe5cad39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bot_runtimes",
        sa.Column("bot_instance_id", sa.Integer(), nullable=False),
        sa.Column("credential_env_key", sa.String(length=120), nullable=True),
        sa.Column("expected_username", sa.String(length=120), nullable=True),
        sa.Column("mode", sa.String(length=20), server_default="polling", nullable=False),
        sa.Column("runtime_token_hash", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_username", sa.String(length=120), nullable=True),
        sa.Column("connected_user_id", sa.String(length=120), nullable=True),
        sa.Column("runtime_version", sa.String(length=120), nullable=True),
        sa.Column("last_error_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bot_instance_id"], ["bot_instances.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("bot_instance_id"),
    )


def downgrade() -> None:
    op.drop_table("bot_runtimes")
