"""Tenant-owned FAQ and knowledge documents.

Revision ID: e73fad4b9c28
Revises: d62e9c3a8b17
Create Date: 2026-08-12 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e73fad4b9c28"
down_revision: str | None = "d62e9c3a8b17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_tenant(table_name: str) -> None:
    op.add_column(table_name, sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        f"fk_{table_name}_bot_instance_id",
        table_name,
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        f"""
        UPDATE {table_name}
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column(table_name, "bot_instance_id", nullable=False)
    op.create_index(f"ix_{table_name}_bot_instance_id", table_name, ["bot_instance_id"])


def upgrade() -> None:
    _add_tenant("kb_faq")
    _add_tenant("kb_documents")


def downgrade() -> None:
    for table_name in ("kb_documents", "kb_faq"):
        op.execute(
            f"""
            DELETE FROM {table_name}
            WHERE bot_instance_id <> (SELECT id FROM bot_instances WHERE slug = 'default')
            """
        )
        op.drop_index(f"ix_{table_name}_bot_instance_id", table_name=table_name)
        op.drop_constraint(
            f"fk_{table_name}_bot_instance_id",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "bot_instance_id")

