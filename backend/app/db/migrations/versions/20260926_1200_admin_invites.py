"""admin_invites

Revision ID: 4c8d2e6f1a90
Revises: 796ed462577d
Create Date: 2026-09-26 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4c8d2e6f1a90"
down_revision: str | None = "796ed462577d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("staff_role", sa.String(16), nullable=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('platform', 'bot_staff')", name="ck_admin_invites_kind"),
        sa.CheckConstraint(
            "(kind = 'platform') = (bot_instance_id IS NULL)",
            name="ck_admin_invites_kind_bot",
        ),
        sa.CheckConstraint(
            "used_count >= 0 AND used_count <= max_uses",
            name="ck_admin_invites_used_count",
        ),
        sa.UniqueConstraint("token_hash", name="uq_admin_invites_token_hash"),
    )
    op.create_index("ix_admin_invites_bot_instance_id", "admin_invites", ["bot_instance_id"])


def downgrade() -> None:
    op.drop_index("ix_admin_invites_bot_instance_id", table_name="admin_invites")
    op.drop_table("admin_invites")
