"""Reuse consent_notice_texts for the admin-editable policy document page (Task 066)

Widens `key` to fit policy_document_html and seeds a placeholder so the page always renders
something rather than an empty body until an admin fills in the real text.

Revision ID: 86b090bc281d
Revises: de77815643d0
Create Date: 2026-09-11 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "86b090bc281d"
down_revision: str | None = "de77815643d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PLACEHOLDER = "<p>Документ ещё не заполнен администратором платформы.</p>"


def upgrade() -> None:
    op.alter_column(
        "consent_notice_texts",
        "key",
        type_=sa.String(32),
        existing_type=sa.String(8),
    )
    op.execute(
        sa.text(
            "INSERT INTO consent_notice_texts (key, value) VALUES ('policy_document_html', :v)"
        ).bindparams(v=_PLACEHOLDER)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM consent_notice_texts WHERE key = 'policy_document_html'")
    )
    op.alter_column(
        "consent_notice_texts",
        "key",
        type_=sa.String(8),
        existing_type=sa.String(32),
    )
