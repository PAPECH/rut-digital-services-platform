from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modules.knowledge_base.application.use_cases import (
    CreateKbDocument,
    create_faq_mirror,
)
from ...modules.knowledge_base.domain.entities import KbFaq
from ...modules.knowledge_base.infrastructure.embedding import FastEmbedEmbeddingPort
from ...modules.knowledge_base.infrastructure.models import KbDocumentRecord, KbFaqRecord
from ...modules.knowledge_base.infrastructure.repositories import (
    SqlAlchemyKbDocumentRepository,
    SqlAlchemyKbFaqRepository,
)
from .archive import ContentExportImportError


def export_faq(session: Session, bot_id: int) -> list[dict[str, Any]]:
    records = session.execute(
        select(KbFaqRecord).where(KbFaqRecord.bot_instance_id == bot_id)
    ).scalars().all()
    return [
        {
            "id": record.id,
            "question": record.question,
            "answer": record.answer,
            "is_active": record.is_active,
            "order": record.order,
        }
        for record in records
    ]


def export_standalone_documents(session: Session, bot_id: int) -> list[dict[str, Any]]:
    records = session.execute(
        select(KbDocumentRecord).where(
            KbDocumentRecord.bot_instance_id == bot_id,
            KbDocumentRecord.source_faq_id.is_(None),
        )
    ).scalars().all()
    return [
        {
            "topic": record.topic,
            "content": record.content,
            "tags": record.tags,
            "is_active": record.is_active,
        }
        for record in records
    ]


def guard_target_empty(session: Session, bot_id: int) -> None:
    has_faq = session.execute(
        select(KbFaqRecord.id).where(KbFaqRecord.bot_instance_id == bot_id).limit(1)
    ).scalar_one_or_none()
    has_document = session.execute(
        select(KbDocumentRecord.id)
        .where(KbDocumentRecord.bot_instance_id == bot_id)
        .limit(1)
    ).scalar_one_or_none()
    if has_faq is not None or has_document is not None:
        raise ContentExportImportError(
            "target bot already has FAQ or knowledge-base documents -- refusing to import kb"
        )


def _embedding_missing(session: Session, document_id: int | None) -> bool:
    assert document_id is not None
    record = session.get(KbDocumentRecord, document_id)
    assert record is not None
    return record.embedding is None


def import_knowledge_base(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
) -> dict[str, int]:
    document_repository = SqlAlchemyKbDocumentRepository(session)
    faq_repository = SqlAlchemyKbFaqRepository(session)
    embedder = FastEmbedEmbeddingPort()
    create_document = CreateKbDocument(document_repository, embedder)
    missing_embeddings = 0

    for document in manifest["kb_documents"]:
        created = create_document.execute(
            bot_instance_id=bot_id,
            topic=document["topic"],
            content=document["content"],
            tags=document["tags"],
            is_active=document["is_active"],
            uploaded_by=None,
        )
        missing_embeddings += int(_embedding_missing(session, created.id))

    for faq_data in manifest["kb_faq"]:
        faq = faq_repository.add(
            KbFaq(
                id=None,
                bot_instance_id=bot_id,
                question=faq_data["question"],
                answer=faq_data["answer"],
                is_active=faq_data["is_active"],
                order=faq_data["order"],
            )
        )
        mirror = create_faq_mirror(faq, document_repository, embedder)
        missing_embeddings += int(_embedding_missing(session, mirror.id))

    return {
        "kb_faq": len(manifest["kb_faq"]),
        "kb_documents": len(manifest["kb_documents"]),
        "missing_embeddings": missing_embeddings,
    }
