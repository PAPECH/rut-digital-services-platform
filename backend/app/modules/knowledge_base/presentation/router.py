from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_admin
from ....core.errors import conflict, not_found
from ....db.session import get_db
from ....services.rate_limit import rate_limit
from ...bot_instances.domain.entities import BotInstance
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.settings import kb_overrides
from ..application.use_cases import (
    BulkReplaceKbDocuments,
    CreateKbDocument,
    KbDocumentNotFound,
    MatchKnowledgeBase,
    PatchKbDocument,
)
from ..domain.entities import KbDocument, MatchResult, MatchTier
from ..infrastructure.embedding import FastEmbedEmbeddingPort
from ..infrastructure.repositories import SqlAlchemyKbDocumentRepository
from .schemas import (
    KbBulkIn,
    KbDocumentIn,
    KbDocumentOut,
    KbDocumentPatch,
    KbTestMatchCandidate,
    KbTestMatchHit,
    KbTestMatchIn,
    KbTestMatchOut,
)

router = APIRouter()

_kb_test_match_rl = rate_limit("kb_test_match", limit=30, window_seconds=60)

_MIRROR_READ_ONLY_MESSAGE = (
    "Документ создан автоматически из FAQ — редактируйте и удаляйте его через /faq/{id}"
)


def _reject_faq_mirror(document: KbDocument | None) -> None:
    if document is not None and document.source_faq_id is not None:
        raise conflict(_MIRROR_READ_ONLY_MESSAGE, code="kb_document_is_faq_mirror")

_TEST_MATCH_NOTES = {
    MatchTier.NO_MATCH: "Ничего похожего не найдено — ни авто-ответа, ни кандидатов.",
    MatchTier.ESCALATE: (
        "Текст совпадает с фразой явного запроса человека — матчинг по базе знаний "
        "не выполняется, сразу эскалация."
    ),
    MatchTier.SKIP: (
        "Матчинг не выполнялся: AI_PROVIDER выключен, пустой текст или модель "
        "эмбеддингов недоступна."
    ),
}


def _to_test_match_out(match: MatchResult) -> KbTestMatchOut:
    if match.tier == MatchTier.AUTO and match.hit is not None:
        return KbTestMatchOut(
            tier=match.tier.value,
            hit=KbTestMatchHit(
                document_id=match.hit.document_id,
                topic=match.hit.topic,
                content=match.hit.answer,
                score=match.hit.score,
            ),
        )
    if match.tier == MatchTier.CANDIDATES:
        return KbTestMatchOut(
            tier=match.tier.value,
            candidates=[
                KbTestMatchCandidate(document_id=c.document_id, topic=c.topic, score=c.score)
                for c in match.candidates
            ],
        )
    return KbTestMatchOut(tier=match.tier.value, note=_TEST_MATCH_NOTES.get(match.tier))


@router.post("/test-match", response_model=KbTestMatchOut, dependencies=[Depends(_kb_test_match_rl)])
def test_match(
    payload: KbTestMatchIn,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
) -> KbTestMatchOut:
    """Песочница для настройки релевантности: гоняет реальный матчинг против введённого
    текста этого бота — ничего не сохраняет и никому не рассылает (нет Message, нет
    websocket-broadcast, нет тикета)."""
    use_case = MatchKnowledgeBase(SqlAlchemyKbDocumentRepository(db), FastEmbedEmbeddingPort())
    match = use_case.execute(bot.id, payload.text, **kb_overrides(bot.settings))
    return _to_test_match_out(match)


@router.get("/documents", response_model=list[KbDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    return SqlAlchemyKbDocumentRepository(db).list_all(bot.id)


@router.post("/documents", response_model=list[KbDocumentOut])
def upload_documents(
    payload: KbBulkIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    """Bulk-загрузка. Если replace=true — затирает существующие документы."""
    use_case = BulkReplaceKbDocuments(SqlAlchemyKbDocumentRepository(db), FastEmbedEmbeddingPort())
    created = use_case.execute(
        bot_instance_id=bot.id,
        documents=[(doc.topic, doc.content, doc.tags, doc.is_active) for doc in payload.documents],
        replace=payload.replace,
        uploaded_by=p.admin_id,
    )
    db.commit()
    return created


@router.post("/documents/one", response_model=KbDocumentOut, status_code=201)
def create_document(
    payload: KbDocumentIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    use_case = CreateKbDocument(SqlAlchemyKbDocumentRepository(db), FastEmbedEmbeddingPort())
    document = use_case.execute(
        bot_instance_id=bot.id,
        topic=payload.topic,
        content=payload.content,
        tags=payload.tags,
        is_active=payload.is_active,
        uploaded_by=p.admin_id,
    )
    db.commit()
    return document


@router.patch("/documents/{document_id}", response_model=KbDocumentOut)
def patch_document(
    document_id: int,
    payload: KbDocumentPatch,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    repository = SqlAlchemyKbDocumentRepository(db)
    _reject_faq_mirror(repository.get(document_id, bot.id))
    use_case = PatchKbDocument(repository, FastEmbedEmbeddingPort())
    try:
        document = use_case.execute(
            document_id=document_id,
            bot_instance_id=bot.id,
            changes=payload.model_dump(exclude_unset=True),
        )
    except KbDocumentNotFound:
        raise not_found("Документ не найден") from None
    db.commit()
    return document


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: CurrentPrincipal = Depends(require_admin),
    bot: BotInstance = Depends(require_tenant_access),
):
    repository = SqlAlchemyKbDocumentRepository(db)
    _reject_faq_mirror(repository.get(document_id, bot.id))
    try:
        repository.delete(document_id, bot.id)
    except LookupError:
        raise not_found("Документ не найден") from None
    db.commit()
