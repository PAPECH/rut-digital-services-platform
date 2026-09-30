"""RUT schedule: add institute_external_id to rut_schedule_manual_sync_requests, for a manual
sync scoped to a whole institute (not just one group or all groups) -- follow-up to Task 045.

Revision ID: be95e962aecd
Revises: a5bcd1f2ddd0
Create Date: 2026-09-02 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "be95e962aecd"
down_revision: str | None = "a5bcd1f2ddd0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rut_schedule_manual_sync_requests",
        sa.Column("institute_external_id", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_rut_schedule_manual_sync_requests_institute_external_id",
        "rut_schedule_manual_sync_requests",
        ["institute_external_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rut_schedule_manual_sync_requests_institute_external_id",
        table_name="rut_schedule_manual_sync_requests",
    )
    op.drop_column("rut_schedule_manual_sync_requests", "institute_external_id")
