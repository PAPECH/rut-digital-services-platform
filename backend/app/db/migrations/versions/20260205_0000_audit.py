"""audit_log table

Revision ID: 0003_audit
Revises: 0002_attachments
Create Date: 2026-02-05 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_audit"
down_revision: Union[str, None] = "0002_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("admins.id", ondelete="SET NULL")),
        sa.Column("ip", sa.String(64)),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text())),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
