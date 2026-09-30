"""RUT schedule: cache the term's date range per group (needed to map a calendar date to
week_parity 1/2 for the day-by-day mini-app view).

Revision ID: 0f2be8c7f735
Revises: 40ed7f5258ee
Create Date: 2026-09-02 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0f2be8c7f735"
down_revision: str | None = "40ed7f5258ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rut_schedule_group_sync", sa.Column("semester_start", sa.Date(), nullable=True))
    op.add_column("rut_schedule_group_sync", sa.Column("semester_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("rut_schedule_group_sync", "semester_end")
    op.drop_column("rut_schedule_group_sync", "semester_start")
