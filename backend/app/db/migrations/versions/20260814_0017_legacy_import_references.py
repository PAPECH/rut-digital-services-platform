"""Add idempotency references for legacy data imports.

Revision ID: 2df4c6f2a9b1
Revises: 8e2c7a1d4f90
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "2df4c6f2a9b1"
down_revision: str | None = "8e2c7a1d4f90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "legacy_import_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_instance_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(length=24), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "bot_instance_id",
            "source_key",
            "entity_type",
            "source_record_id",
            name="uq_legacy_import_reference_source",
        ),
    )
    op.create_index(
        "ix_legacy_import_references_bot_instance_id",
        "legacy_import_references",
        ["bot_instance_id"],
    )
    op.create_index(
        "ix_legacy_import_references_bot_source",
        "legacy_import_references",
        ["bot_instance_id", "source_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_legacy_import_references_bot_source", table_name="legacy_import_references")
    op.drop_index("ix_legacy_import_references_bot_instance_id", table_name="legacy_import_references")
    op.drop_table("legacy_import_references")
