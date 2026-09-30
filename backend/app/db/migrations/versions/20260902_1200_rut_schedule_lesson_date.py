"""RUT schedule: add lesson_date to rut_schedule_lessons, for "Разовое" (type=2) group pages'
explicitly dated, non-recurring sessions -- see docs/tasks/043-rut-schedule-capability.md,
"Addendum, 2026-09-02". Additive and nullable: existing recurring (weekday/week_parity) rows are
unaffected and keep leaving it null.

Revision ID: 8c85dbc526fb
Revises: 3c9a1f6b7d02
Create Date: 2026-09-02 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c85dbc526fb"
down_revision: str | None = "3c9a1f6b7d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rut_schedule_lessons", sa.Column("lesson_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("rut_schedule_lessons", "lesson_date")
