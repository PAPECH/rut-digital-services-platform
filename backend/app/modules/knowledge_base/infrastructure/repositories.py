from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..domain.entities import KbDocument, KbFaq, ScoredDocument
from .models import KbDocumentRecord, KbFaqRecord


def _document_to_domain(record: KbDocumentRecord) -> KbDocument:
    return KbDocument(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        topic=record.topic,
        content=record.content,
        tags=list(record.tags) if record.tags else None,
        is_active=record.is_active,
        uploaded_by=record.uploaded_by,
        created_at=record.created_at,
        source_faq_id=record.source_faq_id,
    )


def _faq_to_domain(record: KbFaqRecord) -> KbFaq:
    return KbFaq(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        question=record.question,
        answer=record.answer,
        is_active=record.is_active,
        order=record.order,
    )


class SqlAlchemyKbDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: KbDocument, *, embedding: list[float] | None) -> KbDocument:
        record = KbDocumentRecord(
            bot_instance_id=document.bot_instance_id,
            topic=document.topic,
            content=document.content,
            tags=document.tags,
            is_active=document.is_active,
            uploaded_by=document.uploaded_by,
            embedding=embedding,
            source_faq_id=document.source_faq_id,
        )
        self._session.add(record)
        self._session.flush()
        return _document_to_domain(record)

    def get(self, document_id: int, bot_instance_id: int) -> KbDocument | None:
        record = self._session.execute(
            select(KbDocumentRecord).where(
                KbDocumentRecord.id == document_id,
                KbDocumentRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        return _document_to_domain(record) if record else None

    def get_by_source_faq_id(self, faq_id: int, bot_instance_id: int) -> KbDocument | None:
        record = self._session.execute(
            select(KbDocumentRecord).where(
                KbDocumentRecord.source_faq_id == faq_id,
                KbDocumentRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        return _document_to_domain(record) if record else None

    def list_all(self, bot_instance_id: int) -> list[KbDocument]:
        records = self._session.execute(
            select(KbDocumentRecord)
            .where(KbDocumentRecord.bot_instance_id == bot_instance_id)
            .order_by(KbDocumentRecord.created_at.desc())
        ).scalars()
        return [_document_to_domain(record) for record in records]

    def update(
        self,
        document: KbDocument,
        *,
        recompute_embedding: bool,
        embedding: list[float] | None = None,
    ) -> KbDocument:
        assert document.id is not None
        record = self._session.execute(
            select(KbDocumentRecord).where(
                KbDocumentRecord.id == document.id,
                KbDocumentRecord.bot_instance_id == document.bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(document.id)
        record.topic = document.topic
        record.content = document.content
        record.tags = document.tags
        record.is_active = document.is_active
        if recompute_embedding:
            record.embedding = embedding
        self._session.flush()
        return _document_to_domain(record)

    def delete(self, document_id: int, bot_instance_id: int) -> None:
        record = self._session.execute(
            select(KbDocumentRecord).where(
                KbDocumentRecord.id == document_id,
                KbDocumentRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(document_id)
        self._session.delete(record)
        self._session.flush()

    def delete_all(self, bot_instance_id: int) -> None:
        # Зеркала FAQ (source_faq_id IS NOT NULL) исключены: bulk-replace документов
        # не должен молча удалять зеркало, оставляя FAQ без пары до следующего
        # редактирования/backfill'а — см. docs/tasks/052-faq-kb-mirroring.md.
        self._session.execute(
            delete(KbDocumentRecord).where(
                KbDocumentRecord.bot_instance_id == bot_instance_id,
                KbDocumentRecord.source_faq_id.is_(None),
            )
        )

    def find_nearest(
        self,
        bot_instance_id: int,
        query_vector: list[float],
        limit: int,
    ) -> list[ScoredDocument]:
        distance = KbDocumentRecord.embedding.cosine_distance(query_vector)
        rows = self._session.execute(
            select(
                KbDocumentRecord.id,
                KbDocumentRecord.topic,
                KbDocumentRecord.content,
                distance.label("distance"),
            )
            .where(
                KbDocumentRecord.bot_instance_id == bot_instance_id,
                KbDocumentRecord.is_active.is_(True),
                KbDocumentRecord.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            ScoredDocument(id=row.id, topic=row.topic, content=row.content, score=1.0 - row.distance)
            for row in rows
        ]

    def list_missing_embeddings(self) -> list[KbDocument]:
        # Без фильтра по is_active: включение документа (PATCH только is_active)
        # эмбеддинг не пересчитывает, так что выключенный документ без вектора
        # остался бы невидимым для поиска и после включения.
        records = (
            self._session.execute(
                select(KbDocumentRecord).where(KbDocumentRecord.embedding.is_(None))
            )
            .scalars()
            .all()
        )
        return [_document_to_domain(record) for record in records]

    def set_embedding(self, document_id: int, bot_instance_id: int, embedding: list[float]) -> None:
        record = self._session.execute(
            select(KbDocumentRecord).where(
                KbDocumentRecord.id == document_id,
                KbDocumentRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(document_id)
        record.embedding = embedding
        self._session.flush()


class SqlAlchemyKbFaqRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, faq: KbFaq) -> KbFaq:
        record = KbFaqRecord(
            bot_instance_id=faq.bot_instance_id,
            question=faq.question,
            answer=faq.answer,
            is_active=faq.is_active,
            order=faq.order,
        )
        self._session.add(record)
        self._session.flush()
        return _faq_to_domain(record)

    def get(self, faq_id: int, bot_instance_id: int) -> KbFaq | None:
        record = self._session.execute(
            select(KbFaqRecord).where(
                KbFaqRecord.id == faq_id,
                KbFaqRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        return _faq_to_domain(record) if record else None

    def list_all(self, bot_instance_id: int, *, active_only: bool) -> list[KbFaq]:
        query = (
            select(KbFaqRecord)
            .where(KbFaqRecord.bot_instance_id == bot_instance_id)
            .order_by(KbFaqRecord.order, KbFaqRecord.id)
        )
        if active_only:
            query = query.where(KbFaqRecord.is_active.is_(True))
        records = self._session.execute(query).scalars()
        return [_faq_to_domain(record) for record in records]

    def update(self, faq: KbFaq) -> KbFaq:
        assert faq.id is not None
        record = self._session.execute(
            select(KbFaqRecord).where(
                KbFaqRecord.id == faq.id,
                KbFaqRecord.bot_instance_id == faq.bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(faq.id)
        record.question = faq.question
        record.answer = faq.answer
        record.is_active = faq.is_active
        record.order = faq.order
        self._session.flush()
        return _faq_to_domain(record)

    def delete(self, faq_id: int, bot_instance_id: int) -> None:
        record = self._session.execute(
            select(KbFaqRecord).where(
                KbFaqRecord.id == faq_id,
                KbFaqRecord.bot_instance_id == bot_instance_id,
            )
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(faq_id)
        self._session.delete(record)
        self._session.flush()

    def list_missing_mirrors(self) -> list[KbFaq]:
        """Платформенно (без bot_instance_id) — тот же паттерн, что и
        KbDocumentRepository.list_missing_embeddings, для одноразового backfill'а
        при старте процесса (main.py)."""
        mirrored_faq_ids = select(KbDocumentRecord.source_faq_id).where(
            KbDocumentRecord.source_faq_id.is_not(None)
        )
        records = self._session.execute(
            select(KbFaqRecord).where(
                KbFaqRecord.is_active.is_(True),
                KbFaqRecord.id.not_in(mirrored_faq_ids),
            )
        ).scalars()
        return [_faq_to_domain(record) for record in records]
