"""pgvector extension + kb_documents.embedding for semantic auto-reply matching (Task 038)

Revision ID: 9b4e1f7a2c53
Revises: d3e5a7c9b1f2
Create Date: 2026-08-25 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "9b4e1f7a2c53"
down_revision: str | None = "d3e5a7c9b1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Должно совпадать с KB_EMBEDDING_DIM в app/modules/knowledge_base/infrastructure/models.py.
_EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "kb_documents",
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kb_documents", "embedding")
    # vector extension не сносим — не знаем, что ещё от неё зависит на момент downgrade.
