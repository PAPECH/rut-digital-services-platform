"""Message.ai_classification -> real enum + kb_document_id FK (Task 051)

Revision ID: 0bb836ad619c
Revises: 01d4fc1875d1
Create Date: 2026-09-10 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0bb836ad619c"
down_revision: str | None = "01d4fc1875d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_NAME = "message_ai_classification_enum"
_ENUM_VALUES = (
    "empty",
    "certificate",
    "payment",
    "dorm",
    "general",
    "kb_staff_requested_text",
    "kb_auto",
    "kb_candidates",
    "kb_no_match",
    "kb_staff_requested",
    "kb_selected",
    "legacy_unknown",
)
_RECOGNIZED = ", ".join(f"'{v}'" for v in _ENUM_VALUES)


def upgrade() -> None:
    # 1. Enum-тип создаётся идемпотентно, тем же DO-блоком, что и в 20260101_0000_init.py.
    quoted = ", ".join(f"'{v}'" for v in _ENUM_VALUES)
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {_ENUM_NAME} AS ENUM ({quoted});
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # 2. kb_document_id добавляется без FK — backfill ниже может ссылаться на уже
    # удалённый документ (deleted до этой миграции), и FK-constraint не должен
    # мешать backfill'у решить это через NULL до того, как constraint появится.
    op.add_column("messages", sa.Column("kb_document_id", sa.Integer(), nullable=True))

    # 3. Раньше id документа зашивался в строку (kb:{id}/kb_selected:{id}) — вынимаем
    # его в новую колонку, но только если документ всё ещё существует (иначе остаётся
    # NULL, ровно как задумано для ON DELETE SET NULL ниже).
    op.execute(
        """
        UPDATE messages
        SET kb_document_id = (substring(ai_classification from '^kb:(\\d+)$'))::integer
        WHERE ai_classification ~ '^kb:\\d+$'
          AND (substring(ai_classification from '^kb:(\\d+)$'))::integer IN (SELECT id FROM kb_documents)
        """
    )
    op.execute(
        """
        UPDATE messages
        SET kb_document_id = (substring(ai_classification from '^kb_selected:(\\d+)$'))::integer
        WHERE ai_classification ~ '^kb_selected:\\d+$'
          AND (substring(ai_classification from '^kb_selected:(\\d+)$'))::integer IN (SELECT id FROM kb_documents)
        """
    )

    # 4. Переписываем сам ai_classification в новый словарь значений: id-суффиксные
    # варианты схлопываются в kb_auto/kb_selected (id теперь живёт в kb_document_id),
    # всё остальное нераспознанное (в т.ч. будущий мусор из cli/import_legacy.py,
    # которым эта миграция не управляет) уходит в legacy_unknown, NULL остаётся NULL.
    op.execute("UPDATE messages SET ai_classification = 'kb_auto' WHERE ai_classification ~ '^kb:\\d+$'")
    op.execute(
        "UPDATE messages SET ai_classification = 'kb_selected' "
        "WHERE ai_classification ~ '^kb_selected:\\d+$'"
    )
    op.execute(
        f"""
        UPDATE messages
        SET ai_classification = 'legacy_unknown'
        WHERE ai_classification IS NOT NULL
          AND ai_classification NOT IN ({_RECOGNIZED})
        """
    )

    # 5. Теперь безопасно добавить FK (все значения NULL либо ссылаются на реально
    # существующий документ) и сменить тип колонки на enum (все значения — легальные
    # члены после шага 4).
    op.create_foreign_key(
        "fk_messages_kb_document_id",
        "messages",
        "kb_documents",
        ["kb_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_messages_kb_document_id"), "messages", ["kb_document_id"], unique=False
    )

    op.execute(
        f"ALTER TABLE messages "
        f"ALTER COLUMN ai_classification TYPE {_ENUM_NAME} "
        f"USING ai_classification::{_ENUM_NAME}"
    )


def downgrade() -> None:
    # Данные не восстанавливаются к исходному kb:{id}/kb_selected:{id} виду — это
    # стандартная для этого репозитория цена downgrade у деструктивных миграций.
    op.execute(
        "ALTER TABLE messages ALTER COLUMN ai_classification TYPE VARCHAR(120) "
        "USING ai_classification::text"
    )
    op.drop_index(op.f("ix_messages_kb_document_id"), table_name="messages")
    op.drop_constraint("fk_messages_kb_document_id", "messages", type_="foreignkey")
    op.drop_column("messages", "kb_document_id")
    op.execute(f"DROP TYPE IF EXISTS {_ENUM_NAME}")
