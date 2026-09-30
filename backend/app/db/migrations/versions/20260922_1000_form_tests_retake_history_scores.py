"""Per-test retake, attempt-history visibility, and score visibility settings (Task 075)

Revision ID: 5c8e0f3a9d21
Revises: 4f6b1c8e2a91
Create Date: 2026-09-22 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c8e0f3a9d21"
down_revision: str | None = "4f6b1c8e2a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "form_test_drafts",
        sa.Column("allow_retake", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "form_test_drafts",
        sa.Column("show_attempt_history", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "form_test_drafts",
        sa.Column("show_scores", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("form_test_drafts", "allow_retake", server_default=None)
    op.alter_column("form_test_drafts", "show_attempt_history", server_default=None)
    op.alter_column("form_test_drafts", "show_scores", server_default=None)

    op.add_column(
        "form_test_versions",
        sa.Column("allow_retake", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "form_test_versions",
        sa.Column("show_attempt_history", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "form_test_versions",
        sa.Column("show_scores", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("form_test_versions", "allow_retake", server_default=None)
    op.alter_column("form_test_versions", "show_attempt_history", server_default=None)
    op.alter_column("form_test_versions", "show_scores", server_default=None)

    # Was a plain UNIQUE(user_id, test_version_id) -- relaxed to "at most one *in-progress*
    # attempt per user per version" so a retake (when the version's own `allow_retake` is true)
    # can create a second, independent `completed` row without disturbing the first. Every
    # existing attempt is already unique per (user, version) under the old constraint, so it
    # trivially satisfies this weaker one -- no backfill needed.
    op.drop_constraint("uq_form_test_attempts_user_version", "form_test_attempts", type_="unique")
    op.create_index(
        "uq_form_test_attempts_user_version_in_progress",
        "form_test_attempts",
        ["user_id", "test_version_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )


def downgrade() -> None:
    # Note: this fails if any (user, version) pair accumulated more than one attempt via a real
    # retake while this migration was applied -- the strict unique constraint cannot represent
    # that history. Downgrading a database with real retake data requires deciding which attempt
    # per pair to keep first; not automated here since that decision is a product call, not a
    # mechanical one.
    op.drop_index("uq_form_test_attempts_user_version_in_progress", table_name="form_test_attempts")
    op.create_unique_constraint(
        "uq_form_test_attempts_user_version", "form_test_attempts", ["user_id", "test_version_id"]
    )

    op.drop_column("form_test_versions", "show_scores")
    op.drop_column("form_test_versions", "show_attempt_history")
    op.drop_column("form_test_versions", "allow_retake")

    op.drop_column("form_test_drafts", "show_scores")
    op.drop_column("form_test_drafts", "show_attempt_history")
    op.drop_column("form_test_drafts", "allow_retake")
