"""RUT schedule: platform-admin manual sync trigger + live log (Task 045). Never written by the
nightly cron -- only an explicit admin-triggered run creates a row here.

Revision ID: a5bcd1f2ddd0
Revises: 8c85dbc526fb
Create Date: 2026-09-02 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5bcd1f2ddd0"
down_revision: str | None = "8c85dbc526fb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rut_schedule_manual_sync_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id",
            sa.Integer(),
            sa.ForeignKey("capability_installations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("group_external_id", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("groups_synced", sa.Integer(), nullable=True),
        sa.Column("groups_failed", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_rut_schedule_manual_sync_requests_bot_instance_id",
        "rut_schedule_manual_sync_requests",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_rut_schedule_manual_sync_requests_installation_id",
        "rut_schedule_manual_sync_requests",
        ["installation_id"],
    )
    op.create_index(
        "ix_rut_schedule_manual_sync_requests_group_external_id",
        "rut_schedule_manual_sync_requests",
        ["group_external_id"],
    )
    op.create_index(
        "ix_rut_schedule_manual_sync_requests_status",
        "rut_schedule_manual_sync_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("rut_schedule_manual_sync_requests")
