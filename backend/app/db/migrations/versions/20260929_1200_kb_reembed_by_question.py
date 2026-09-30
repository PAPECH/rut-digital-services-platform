"""Reset kb_documents.embedding so every document is re-embedded by question/topic only (Task 089)

`passage_text()` no longer includes the document content/answer — only topic + tags. Vectors
stored before this change were computed from topic + tags + content, so they are nulled here and
recomputed in the new format by the startup backfill (`backfill_missing_embeddings` in
`app/main.py`), which runs after `alembic upgrade head` in `entrypoint.sh` and inside the app
lifespan before the api starts serving — so there is no window with unsearchable documents, only
a slightly longer api start (one embedding per document, CPU).

Safe to run more than once. Downgrade is a no-op: old-format vectors cannot be restored, and the
startup backfill only fills NULLs, so the old code would simply keep the new-format vectors.

Revision ID: 5c8d2e4f6a19
Revises: b9d81e7a3c24
Create Date: 2026-09-29 12:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5c8d2e4f6a19"
down_revision: str | None = "b9d81e7a3c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE kb_documents SET embedding = NULL")


def downgrade() -> None:
    pass
