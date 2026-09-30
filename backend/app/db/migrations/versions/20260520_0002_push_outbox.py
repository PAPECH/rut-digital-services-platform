"""push_outbox table

Revision ID: 0006_push_outbox
Revises: 0005_user_trgm
Create Date: 2026-05-20 02:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_push_outbox"
down_revision: Union[str, None] = "0005_user_trgm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
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
    )
    op.create_index("ix_push_outbox_user_id", "push_outbox", ["user_id"])
    op.create_index("ix_push_outbox_next_retry_at", "push_outbox", ["next_retry_at"])
    op.create_index("ix_push_outbox_sent_at", "push_outbox", ["sent_at"])
    # Частичный индекс на «непосланные» — оптимизация выборки воркера.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_push_outbox_pending "
        "ON push_outbox (next_retry_at) WHERE sent_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_push_outbox_pending")
    op.drop_index("ix_push_outbox_sent_at", table_name="push_outbox")
    op.drop_index("ix_push_outbox_next_retry_at", table_name="push_outbox")
    op.drop_index("ix_push_outbox_user_id", table_name="push_outbox")
    op.drop_table("push_outbox")
