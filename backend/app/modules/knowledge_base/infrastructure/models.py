from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....db.base import Base, TimestampMixin

# Размерность вектора зависит от модели (KB_EMBEDDING_MODEL в core/config.py).
# paraphrase-multilingual-MiniLM-L12-v2 отдаёт 384. Меняешь модель — меняешь и это,
# и миграцию (см. db/migrations/versions/20260825_1800_kb_semantic_embedding.py).
KB_EMBEDDING_DIM = 384


class KbFaqRecord(Base, TimestampMixin):
    __tablename__ = "kb_faq"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class KbDocumentRecord(Base, TimestampMixin):
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_instance_id: Mapped[int] = mapped_column(
        ForeignKey("bot_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSONB)  # list[str] — свободные ключевые слова/синонимы
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(KB_EMBEDDING_DIM), nullable=True)
    # Не-null только для зеркал, автосозданных из KbFaq (Task 052).
    source_faq_id: Mapped[int | None] = mapped_column(
        ForeignKey("kb_faq.id", ondelete="CASCADE"), index=True
    )
