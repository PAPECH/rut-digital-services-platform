"""form_test_attempts.identity_snapshot -- frozen ФИО/birth date/email at completion (Task 080)

Revision ID: 9a1f3e7c5b02
Revises: 7e2b4a9c1f38
Create Date: 2026-09-23 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9a1f3e7c5b02"
down_revision: str | None = "7e2b4a9c1f38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "form_test_attempts",
        sa.Column("identity_snapshot", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("form_test_attempts", "identity_snapshot")
