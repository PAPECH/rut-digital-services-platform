"""Tenant-owned runtime settings.

Revision ID: c41f8b2d7a06
Revises: b95d20f6e301
Create Date: 2026-08-12 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c41f8b2d7a06"
down_revision: str | None = "b95d20f6e301"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("bot_instance_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_app_settings_bot_instance_id",
        "app_settings",
        "bot_instances",
        ["bot_instance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        UPDATE app_settings
        SET bot_instance_id = (SELECT id FROM bot_instances WHERE slug = 'default')
        WHERE bot_instance_id IS NULL
        """
    )
    op.alter_column("app_settings", "bot_instance_id", nullable=False)
    op.drop_constraint("app_settings_pkey", "app_settings", type_="primary")
    op.create_primary_key(
        "app_settings_pkey",
        "app_settings",
        ["bot_instance_id", "key"],
    )
    op.create_index(
        "ix_app_settings_bot_instance_id",
        "app_settings",
        ["bot_instance_id"],
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app_settings
        WHERE bot_instance_id <> (SELECT id FROM bot_instances WHERE slug = 'default')
        """
    )
    op.drop_index("ix_app_settings_bot_instance_id", table_name="app_settings")
    op.drop_constraint("app_settings_pkey", "app_settings", type_="primary")
    op.create_primary_key("app_settings_pkey", "app_settings", ["key"])
    op.drop_constraint("fk_app_settings_bot_instance_id", "app_settings", type_="foreignkey")
    op.drop_column("app_settings", "bot_instance_id")

