from __future__ import annotations

import logging
from dataclasses import replace

from ....core.config import settings
from ..domain.entities import (
    KbDocument,
    KbFaq,
    MatchResult,
    MatchTier,
    decide_tier,
    is_explicit_human_request,
    passage_text,
)
from ..domain.repositories import KbDocumentRepository, KbFaqRepository
from .ports import EmbeddingPort

log = logging.getLogger(__name__)


class MatchKnowledgeBase:
    """Замена free-функции find_answer (services/ai.py) — тот же алгоритм, но
    зависит от портов (EmbeddingPort, KbDocumentRepository), а не от FastAPI/
    SQLAlchemy напрямую."""

    def __init__(self, repository: KbDocumentRepository, embedder: EmbeddingPort) -> None:
        self._repository = repository
        self._embedder = embedder

    def execute(
        self,
        bot_instance_id: int,
        text: str,
        *,
        auto_answer_threshold: float | None = None,
        candidate_min_threshold: float | None = None,
        max_candidates: int | None = None,
    ) -> MatchResult:
        """auto_answer_threshold/candidate_min_threshold/max_candidates — per-bot
        переопределения (BotSettings.knowledge_base, см. application.settings.kb_overrides);
        None использует платформенное значение по умолчанию (settings.KB_*)."""
        text = (text or "").strip()
        if not text:
            return MatchResult(MatchTier.SKIP)
        if settings.AI_PROVIDER != "kb_semantic":
            return MatchResult(MatchTier.SKIP)
        if is_explicit_human_request(text):
            return MatchResult(MatchTier.ESCALATE)

        auto_threshold = (
            settings.KB_AUTO_ANSWER_THRESHOLD if auto_answer_threshold is None else auto_answer_threshold
        )
        candidate_threshold = (
            settings.KB_CANDIDATE_MIN_THRESHOLD
            if candidate_min_threshold is None
            else candidate_min_threshold
        )
        limit = settings.KB_MAX_CANDIDATES if max_candidates is None else max_candidates

        query_vector = self._embedder.embed(text)
        if query_vector is None:
            # Модель недоступна/сбоила — деградируем в «сегодняшнее» поведение
            # (тихо ничего не отвечаем), а не показываем всем «ничего не найдено».
            return MatchResult(MatchTier.SKIP)

        scored = self._repository.find_nearest(bot_instance_id, query_vector, limit)
        log.info(f"{scored=}")
        return decide_tier(
            scored,
            auto_answer_threshold=auto_threshold,
            candidate_min_threshold=candidate_threshold,
            auto_answer_min_margin=settings.KB_AUTO_ANSWER_MIN_MARGIN,
        )


class CreateKbDocument:
    def __init__(self, repository: KbDocumentRepository, embedder: EmbeddingPort) -> None:
        self._repository = repository
        self._embedder = embedder

    def execute(
        self,
        *,
        bot_instance_id: int,
        topic: str,
        content: str,
        tags: list[str] | None,
        is_active: bool,
        uploaded_by: int | None,
        source_faq_id: int | None = None,
    ) -> KbDocument:
        vector = self._embedder.embed(passage_text(topic, tags))
        document = KbDocument(
            id=None,
            bot_instance_id=bot_instance_id,
            topic=topic,
            content=content,
            tags=tags,
            is_active=is_active,
            uploaded_by=uploaded_by,
            source_faq_id=source_faq_id,
        )
        return self._repository.add(document, embedding=vector)


class BulkReplaceKbDocuments:
    """upload_documents (kb.py) — если replace=true, старые документы бота стираются
    перед вставкой новых."""

    def __init__(self, repository: KbDocumentRepository, embedder: EmbeddingPort) -> None:
        self._repository = repository
        self._embedder = embedder

    def execute(
        self,
        *,
        bot_instance_id: int,
        documents: list[tuple[str, str, list[str] | None, bool]],  # (topic, content, tags, is_active)
        replace: bool,
        uploaded_by: int | None,
    ) -> list[KbDocument]:
        if replace:
            self._repository.delete_all(bot_instance_id)

        created: list[KbDocument] = []
        for topic, content, tags, is_active in documents:
            vector = self._embedder.embed(passage_text(topic, tags))
            document = KbDocument(
                id=None,
                bot_instance_id=bot_instance_id,
                topic=topic,
                content=content,
                tags=tags,
                is_active=is_active,
                uploaded_by=uploaded_by,
            )
            created.append(self._repository.add(document, embedding=vector))
        return created


class KbDocumentNotFound(LookupError):
    pass


class PatchKbDocument:
    def __init__(self, repository: KbDocumentRepository, embedder: EmbeddingPort) -> None:
        self._repository = repository
        self._embedder = embedder

    def execute(
        self,
        *,
        document_id: int,
        bot_instance_id: int,
        changes: dict[str, object],
    ) -> KbDocument:
        current = self._repository.get(document_id, bot_instance_id)
        if current is None:
            raise KbDocumentNotFound(document_id)
        updated = replace(current, **changes)
        recompute = bool(changes.keys() & {"topic", "tags"})
        vector = (
            self._embedder.embed(passage_text(updated.topic, updated.tags))
            if recompute
            else None
        )
        return self._repository.update(updated, recompute_embedding=recompute, embedding=vector)


def create_faq_mirror(
    faq: KbFaq,
    document_repository: KbDocumentRepository,
    embedder: EmbeddingPort,
    *,
    uploaded_by: int | None = None,
) -> KbDocument:
    """Создаёт KbDocument-зеркало только что созданного KbFaq — тем же путём
    (CreateKbDocument, эмбеддинг через passage_text), что и обычный документ.
    faq_router.py вызывает это сразу после KbFaqRepository.add(); backfill_faq_mirrors
    ниже — для уже существующих FAQ, у которых зеркала ещё нет."""
    assert faq.id is not None
    use_case = CreateKbDocument(document_repository, embedder)
    return use_case.execute(
        bot_instance_id=faq.bot_instance_id,
        topic=faq.question,
        content=faq.answer,
        tags=None,
        is_active=faq.is_active,
        uploaded_by=uploaded_by,
        source_faq_id=faq.id,
    )


def sync_faq_mirror(
    faq: KbFaq,
    document_repository: KbDocumentRepository,
    embedder: EmbeddingPort,
) -> KbDocument:
    """Обновляет KbDocument-зеркало вслед за PATCH KbFaq — эмбеддинг пересчитывается
    только если изменился question (PatchKbDocument.execute решает это по
    changes-ключу topic — ответ в эмбеддинг не входит, см. passage_text). Зеркала не должно не быть (оно создаётся
    вместе с FAQ), но на случай гонки/ручной правки БД — досоздаёт его, а не падает."""
    assert faq.id is not None
    mirror = document_repository.get_by_source_faq_id(faq.id, faq.bot_instance_id)
    if mirror is None:
        return create_faq_mirror(faq, document_repository, embedder)
    assert mirror.id is not None
    use_case = PatchKbDocument(document_repository, embedder)
    return use_case.execute(
        document_id=mirror.id,
        bot_instance_id=faq.bot_instance_id,
        changes={"topic": faq.question, "content": faq.answer, "is_active": faq.is_active},
    )


def backfill_faq_mirrors(
    faq_repository: KbFaqRepository,
    document_repository: KbDocumentRepository,
    embedder: EmbeddingPort,
) -> int:
    """Досоздаёт зеркала для уже существующих активных FAQ, у которых их ещё нет —
    вызывается один раз при старте процесса (main.py), рядом с
    backfill_missing_embeddings. Идемпотентно: повторный запуск не создаёт дублей,
    поскольку KbFaqRepository.list_missing_mirrors возвращает только FAQ без зеркала."""
    faqs = faq_repository.list_missing_mirrors()
    for faq in faqs:
        create_faq_mirror(faq, document_repository, embedder)
    return len(faqs)


def warm_up_embedding_model(embedder: EmbeddingPort) -> None:
    """Прогревает модель эмбеддингов при старте процесса. Без этого первая загрузка
    (скачивание с HF, если модель не запечена в образ на этапе сборки — см.
    backend/Dockerfile) откладывается до первого реального сообщения пользователя и
    может не уложиться в HTTP-таймаут бот-адаптера (bot/app/backend.py) — снаружи это
    выглядит как «не удалось доставить сообщение специалисту», хотя бэкенд на самом
    деле дообработает запрос и просто не успеет ответить клиенту вовремя."""
    if settings.AI_PROVIDER != "kb_semantic":
        return
    embedder.warm_up()


def backfill_missing_embeddings(repository: KbDocumentRepository, embedder: EmbeddingPort) -> int:
    """Досчитывает embedding для документов, у которых он ещё NULL (новая колонка,
    ручной SQL-импорт и т.п.). Вызывается один раз при старте процесса (main.py) — так
    редактирование через presentation/router.py остаётся единственным путём для новых/
    изменённых документов, а старые данные не требуют отдельной ручной команды
    реиндексации. Не коммитит сама — вызывающий (main.py, играющий роль composition
    root для этого startup-шага, как обычно роутер) решает, когда закоммитить.

    Пустая база знаний — валидный случай (см. warm_up_embedding_model): раньше это
    означало, что цикл ниже не выполняется ни разу и модель вообще не грузится при
    старте."""
    if settings.AI_PROVIDER != "kb_semantic":
        return 0
    documents = repository.list_missing_embeddings()
    updated = 0
    for document in documents:
        vector = embedder.embed(passage_text(document.topic, document.tags))
        if vector is None:
            log.warning("Не удалось посчитать embedding для kb_document id=%s — пропуск", document.id)
            continue
        assert document.id is not None
        repository.set_embedding(document.id, document.bot_instance_id, vector)
        updated += 1
    return updated
