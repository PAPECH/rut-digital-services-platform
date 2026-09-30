"""submission appointment slots

Revision ID: b9d81e7a3c24
Revises: 4c8d2e6f1a90
Create Date: 2026-09-30 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9d81e7a3c24"
down_revision: str | None = "4c8d2e6f1a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "submission_appointment_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("form_submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admins.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "bot_instance_id",
            "starts_at",
            name="uq_submission_appointment_slot_bot_start",
        ),
        sa.UniqueConstraint(
            "submission_id",
            "starts_at",
            name="uq_submission_appointment_slot_submission_start",
        ),
    )
    op.create_index(
        "ix_submission_appointment_slots_bot_instance_id",
        "submission_appointment_slots",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_submission_appointment_slots_submission_id",
        "submission_appointment_slots",
        ["submission_id"],
    )
    op.create_index(
        "ix_submission_appointment_slots_starts_at",
        "submission_appointment_slots",
        ["starts_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_submission_appointment_slots_starts_at",
        table_name="submission_appointment_slots",
    )
    op.drop_index(
        "ix_submission_appointment_slots_submission_id",
        table_name="submission_appointment_slots",
    )
    op.drop_index(
        "ix_submission_appointment_slots_bot_instance_id",
        table_name="submission_appointment_slots",
    )
    op.drop_table("submission_appointment_slots")
