"""Tenant-aware administrative audit.

Revision ID: f84abe5cad39
Revises: e73fad4b9c28
Create Date: 2026-08-12 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f84abe5cad39"
down_revision: str | None = "e73fad4b9c28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_audit_log_bot_instance_id",
        "audit_log",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE audit_log
        SET bot_instance_id = (meta ->> 'bot_instance_id')::integer
        WHERE meta IS NOT NULL
          AND meta ? 'bot_instance_id'
          AND (meta ->> 'bot_instance_id') ~ '^[0-9]+$'
          AND EXISTS (
              SELECT 1 FROM bot_instances
              WHERE bot_instances.id = (audit_log.meta ->> 'bot_instance_id')::integer
          )
        """
    )
    op.create_index("ix_audit_log_bot_instance_id", "audit_log", ["bot_instance_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_bot_instance_id", table_name="audit_log")
    op.drop_constraint("fk_audit_log_bot_instance_id", "audit_log", type_="foreignkey")
    op.drop_column("audit_log", "bot_instance_id")

