"""RUT schedule: drop the per-lesson unique constraint -- a single time slot can legitimately
hold two lessons (different subgroups, same discipline/weekday/week_parity/start_time), which the
constraint incorrectly rejected as a duplicate. `save_schedule` already fully replaces a group's
rows on every sync, so no natural-key uniqueness is needed here at all.

Revision ID: 0e50c9857148
Revises: 0f2be8c7f735
Create Date: 2026-09-02 10:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0e50c9857148"
down_revision: str | None = "0f2be8c7f735"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_rut_schedule_lesson", "rut_schedule_lessons", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_rut_schedule_lesson",
        "rut_schedule_lessons",
        ["bot_instance_id", "group_external_id", "weekday", "week_parity", "start_time", "discipline"],
    )
