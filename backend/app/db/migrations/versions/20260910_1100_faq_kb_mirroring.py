"""kb_documents.source_faq_id link + drop bilingual FAQ fields (Task 052)

Revision ID: a092acf6995a
Revises: 0bb836ad619c
Create Date: 2026-09-10 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a092acf6995a"
down_revision: str | None = "0bb836ad619c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kb_documents", sa.Column("source_faq_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_kb_documents_source_faq_id",
        "kb_documents",
        "kb_faq",
        ["source_faq_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_kb_documents_source_faq_id"), "kb_documents", ["source_faq_id"], unique=False
    )

    # Убираем билингвальность FAQ (подтверждённое решение — не только эмбеддинг
    # зеркала берёт RU-текст, сам FAQ больше не хранит EN-вариант). question_en/
    # answer_en нигде не читаются мимо схем/моделей, потерянные данные не мигрируются
    # никуда — см. docs/tasks/052-faq-kb-mirroring.md. language уже был мёртвой
    # колонкой (не отдавался ни одной схемой) — убираем заодно, раз уже здесь.
    op.drop_column("kb_faq", "question_en")
    op.drop_column("kb_faq", "answer_en")
    op.drop_column("kb_faq", "language")


def downgrade() -> None:
    # Данные question_en/answer_en/language не восстанавливаются — они уже были
    # удалены безвозвратно на момент этого downgrade, колонки возвращаются пустыми.
    op.add_column("kb_faq", sa.Column("language", sa.String(length=16), nullable=True))
    op.add_column("kb_faq", sa.Column("answer_en", sa.Text(), nullable=True))
    op.add_column("kb_faq", sa.Column("question_en", sa.String(length=500), nullable=True))

    op.drop_index(op.f("ix_kb_documents_source_faq_id"), table_name="kb_documents")
    op.drop_constraint("fk_kb_documents_source_faq_id", "kb_documents", type_="foreignkey")
    op.drop_column("kb_documents", "source_faq_id")
