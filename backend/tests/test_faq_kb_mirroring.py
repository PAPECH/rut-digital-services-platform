"""FAQ -> kb_documents mirroring (Task 052) — application-layer behavior against
in-memory fakes (matches this codebase's existing fake-repository unit-test style,
see test_kb_matching.py), plus the presentation-layer read-only guard.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.errors import ApiError
from app.modules.knowledge_base.application.use_cases import (
    PatchKbDocument,
    backfill_faq_mirrors,
    create_faq_mirror,
    sync_faq_mirror,
)
from app.modules.knowledge_base.domain.entities import KbDocument, KbFaq
from app.modules.knowledge_base.presentation.router import _reject_faq_mirror


class _FakeEmbedder:
    def embed(self, _text: str) -> list[float] | None:
        return [0.1, 0.2, 0.3]

    def warm_up(self) -> None:  # pragma: no cover - not exercised here
        pass


class _FakeDocumentRepository:
    """Enough of KbDocumentRepository for create_faq_mirror/sync_faq_mirror."""

    def __init__(self) -> None:
        self._by_id: dict[int, KbDocument] = {}
        self._next_id = 1

    def add(self, document: KbDocument, *, embedding) -> KbDocument:
        record = replace(document, id=self._next_id)
        self._by_id[record.id] = record
        self._next_id += 1
        return record

    def get(self, document_id: int, bot_instance_id: int) -> KbDocument | None:
        doc = self._by_id.get(document_id)
        return doc if doc is not None and doc.bot_instance_id == bot_instance_id else None

    def get_by_source_faq_id(self, faq_id: int, bot_instance_id: int) -> KbDocument | None:
        for doc in self._by_id.values():
            if doc.source_faq_id == faq_id and doc.bot_instance_id == bot_instance_id:
                return doc
        return None

    def update(self, document: KbDocument, *, recompute_embedding: bool, embedding=None) -> KbDocument:
        self._by_id[document.id] = document
        return document

    def list_all(self, bot_instance_id: int) -> list[KbDocument]:
        return [d for d in self._by_id.values() if d.bot_instance_id == bot_instance_id]

    def delete(self, document_id: int, bot_instance_id: int) -> None:
        self._by_id.pop(document_id, None)

    def delete_all(self, bot_instance_id: int) -> None:
        for doc_id, doc in list(self._by_id.items()):
            if doc.bot_instance_id == bot_instance_id and doc.source_faq_id is None:
                del self._by_id[doc_id]

    def find_nearest(self, bot_instance_id, query_vector, limit):  # pragma: no cover
        return []

    def list_missing_embeddings(self):  # pragma: no cover
        return []

    def set_embedding(self, document_id, bot_instance_id, embedding) -> None:  # pragma: no cover
        pass


class _FakeFaqRepository:
    def __init__(self, faqs: list[KbFaq]) -> None:
        self._faqs = faqs

    def list_missing_mirrors(self) -> list[KbFaq]:
        return list(self._faqs)


def test_create_faq_mirror_sets_source_faq_id_and_matches_content() -> None:
    faq = KbFaq(id=5, bot_instance_id=1, question="Когда каникулы?", answer="С 25 декабря")
    repo = _FakeDocumentRepository()

    mirror = create_faq_mirror(faq, repo, _FakeEmbedder(), uploaded_by=9)

    assert mirror.source_faq_id == 5
    assert mirror.topic == "Когда каникулы?"
    assert mirror.content == "С 25 декабря"
    assert mirror.uploaded_by == 9
    assert mirror.bot_instance_id == 1


def test_sync_faq_mirror_updates_existing_mirror_topic_and_content() -> None:
    faq = KbFaq(id=5, bot_instance_id=1, question="Когда каникулы?", answer="С 25 декабря")
    repo = _FakeDocumentRepository()
    create_faq_mirror(faq, repo, _FakeEmbedder())

    updated_faq = replace(faq, question="Когда зимние каникулы?", answer="С 26 декабря")
    mirror = sync_faq_mirror(updated_faq, repo, _FakeEmbedder())

    assert mirror.topic == "Когда зимние каникулы?"
    assert mirror.content == "С 26 декабря"
    assert mirror.source_faq_id == 5
    # Не завелось второго документа — тот же id, что и созданный create_faq_mirror.
    assert len(repo.list_all(1)) == 1


def test_sync_faq_mirror_creates_one_if_missing() -> None:
    # Защита от гонки/ручной правки БД: если зеркала почему-то ещё нет — создаём,
    # а не падаем.
    faq = KbFaq(id=5, bot_instance_id=1, question="Q", answer="A")
    repo = _FakeDocumentRepository()

    mirror = sync_faq_mirror(faq, repo, _FakeEmbedder())

    assert mirror.source_faq_id == 5


def test_backfill_faq_mirrors_creates_missing_and_is_idempotent() -> None:
    faq = KbFaq(id=5, bot_instance_id=1, question="Q", answer="A")
    document_repo = _FakeDocumentRepository()

    created = backfill_faq_mirrors(_FakeFaqRepository([faq]), document_repo, _FakeEmbedder())
    assert created == 1
    assert document_repo.get_by_source_faq_id(5, 1) is not None

    # В реальном репозитории list_missing_mirrors больше не вернул бы уже
    # смирроренный FAQ — здесь это то, что backfill_faq_mirrors должен увидеть на
    # втором проходе: ноль новых документов, не дубликат.
    created_again = backfill_faq_mirrors(_FakeFaqRepository([]), document_repo, _FakeEmbedder())
    assert created_again == 0
    assert len(document_repo.list_all(1)) == 1


def test_reject_faq_mirror_blocks_documents_with_source_faq_id() -> None:
    mirror = KbDocument(
        id=1, bot_instance_id=1, topic="Q", content="A", source_faq_id=5
    )
    with pytest.raises(ApiError) as exc_info:
        _reject_faq_mirror(mirror)
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "kb_document_is_faq_mirror"


def test_reject_faq_mirror_allows_regular_documents_and_none() -> None:
    regular = KbDocument(id=2, bot_instance_id=1, topic="Q", content="A")
    _reject_faq_mirror(regular)  # no raise
    _reject_faq_mirror(None)  # no raise


class _RecordingEmbedder(_FakeEmbedder):
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, text: str) -> list[float] | None:
        self.texts.append(text)
        return super().embed(text)


class _RecordingDocumentRepository(_FakeDocumentRepository):
    def __init__(self) -> None:
        super().__init__()
        self.recomputed: list[bool] = []

    def update(self, document: KbDocument, *, recompute_embedding: bool, embedding=None) -> KbDocument:
        self.recomputed.append(recompute_embedding)
        return super().update(document, recompute_embedding=recompute_embedding, embedding=embedding)


def test_embedding_is_built_from_question_only_not_the_answer() -> None:
    # Task 089: ответ в эмбеддинг не входит — иначе длинный ответ размывает вектор и
    # даже дословный вопрос не находит собственную запись.
    faq = KbFaq(id=5, bot_instance_id=1, question="Как получить место?", answer="Обратитесь в УВП")
    embedder = _RecordingEmbedder()

    create_faq_mirror(faq, _FakeDocumentRepository(), embedder)

    assert embedder.texts == ["Как получить место?"]


def test_answer_only_change_does_not_recompute_embedding() -> None:
    faq = KbFaq(id=5, bot_instance_id=1, question="Как получить место?", answer="Обратитесь в УВП")
    repo = _RecordingDocumentRepository()
    create_faq_mirror(faq, repo, _FakeEmbedder())
    mirror = repo.get_by_source_faq_id(5, 1)
    assert mirror is not None and mirror.id is not None

    embedder = _RecordingEmbedder()
    PatchKbDocument(repo, embedder).execute(
        document_id=mirror.id, bot_instance_id=1, changes={"content": "Новый ответ"}
    )
    assert repo.recomputed == [False]
    assert embedder.texts == []

    PatchKbDocument(repo, embedder).execute(
        document_id=mirror.id, bot_instance_id=1, changes={"topic": "Как заселиться?"}
    )
    assert repo.recomputed == [False, True]
    assert embedder.texts == ["Как заселиться?"]
