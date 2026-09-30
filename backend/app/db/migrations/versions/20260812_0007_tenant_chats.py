"""Tenant-owned chats and staff favorites.

Revision ID: d62e9c3a8b17
Revises: c41f8b2d7a06
Create Date: 2026-08-12 21:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d62e9c3a8b17"
down_revision: str | None = "c41f8b2d7a06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_tenant(column_table: str) -> None:
    op.add_column(column_table, sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        f"fk_{column_table}_bot_instance_id",
        column_table,
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        f"""
        UPDATE {column_table}
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column(column_table, "bot_instance_id", nullable=False)
    op.create_index(
        f"ix_{column_table}_bot_instance_id",
        column_table,
        ["bot_instance_id"],
    )


def upgrade() -> None:
    _add_tenant("messages")
    _add_tenant("staff_favorites")

    op.drop_index("ix_messages_external_id", table_name="messages")
    op.create_unique_constraint(
        "uq_messages_bot_external_id",
        "messages",
        ["bot_instance_id", "external_id"],
    )

    op.drop_constraint("uq_staff_favorites_user_support", "staff_favorites", type_="unique")
    op.create_unique_constraint(
        "uq_staff_favorites_bot_user_support",
        "staff_favorites",
        ["bot_instance_id", "user_id", "support_id"],
    )


def _keep_default_only(table_name: str) -> None:
    op.execute(
        f"""
        DELETE FROM {table_name}
        WHERE bot_instance_id <> (SELECT id FROM bot_instances WHERE slug = 'default')
        """
    )


def downgrade() -> None:
    _keep_default_only("messages")
    _keep_default_only("staff_favorites")

    op.drop_constraint("uq_staff_favorites_bot_user_support", "staff_favorites", type_="unique")
    op.create_unique_constraint(
        "uq_staff_favorites_user_support",
        "staff_favorites",
        ["user_id", "support_id"],
    )

    op.drop_constraint("uq_messages_bot_external_id", "messages", type_="unique")
    op.create_unique_constraint("messages_external_id_key", "messages", ["external_id"])
    op.create_index("ix_messages_external_id", "messages", ["external_id"])

    for table_name in ("staff_favorites", "messages"):
        op.drop_index(f"ix_{table_name}_bot_instance_id", table_name=table_name)
        op.drop_constraint(
            f"fk_{table_name}_bot_instance_id",
            table_name,
            type_="foreignkey",
        )
        op.drop_column(table_name, "bot_instance_id")
