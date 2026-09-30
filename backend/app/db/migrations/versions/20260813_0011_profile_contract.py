"""Separate mandatory shared profile from bot-local custom fields.

Revision ID: e13a7c94b621
Revises: c92df1a4e870
Create Date: 2026-08-13 01:10:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e13a7c94b621"
down_revision: str | None = "c92df1a4e870"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CORE_KEYS = "'last_name', 'first_name', 'patronymic', 'phone', 'phone_verified', 'email', 'birth_date'"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE bot_instances
        SET profile_schema = COALESCE(
            (
                SELECT jsonb_agg(field ORDER BY position)
                FROM jsonb_array_elements(profile_schema) WITH ORDINALITY AS item(field, position)
                WHERE COALESCE(field ->> 'key', '') NOT IN ({_CORE_KEYS})
            ),
            '[]'::jsonb
        )
        """
    )


def downgrade() -> None:
    # Core requirements are application-owned and cannot be reconstructed as tenant settings.
    pass
