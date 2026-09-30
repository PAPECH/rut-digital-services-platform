"""POST /kb/test-match — admin-only relevance sandbox (Task 049).

Endpoint accepts only free text, never a bot/document id, so which bot's
knowledge base gets searched is structurally determined by the server-resolved
`require_tenant_access` dependency alone -- these tests confirm that wiring and
the tier -> response mapping, faking MatchKnowledgeBase itself (the matching
algorithm is already covered in test_kb_matching.py).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_admin
from app.db.session import get_db
from app.modules.bot_instances.domain.entities import BotInstance
from app.modules.knowledge_base.domain.entities import KbCandidate, KbHit, MatchResult, MatchTier
from app.modules.knowledge_base.presentation import router as kb_module
from app.modules.tenancy.presentation.dependencies import require_tenant_access


def _app(bot: BotInstance) -> FastAPI:
    app = FastAPI()
    app.include_router(kb_module.router, prefix="/kb")
    app.dependency_overrides[require_tenant_access] = lambda: bot
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[get_db] = lambda: None
    return app


class _FakeMatchKnowledgeBase:
    """Заменяет kb_module.MatchKnowledgeBase целиком -- репозиторий/эмбеддер всё
    равно конструируются (с db=None), но никогда не используются по-настоящему."""

    _result: MatchResult = MatchResult(MatchTier.SKIP)
    _seen: dict[str, object] | None = None

    def __init__(self, _repository, _embedder) -> None:
        pass

    def execute(self, bot_instance_id, text, **overrides):
        if self._seen is not None:
            self._seen["bot_instance_id"] = bot_instance_id
            self._seen["text"] = text
            self._seen["overrides"] = overrides
        return self._result


def _fake_match_knowledge_base(monkeypatch, *, result: MatchResult, seen: dict[str, object] | None = None):
    fake = type("_FakeMatchKnowledgeBase", (_FakeMatchKnowledgeBase,), {"_result": result, "_seen": seen})
    monkeypatch.setattr(kb_module, "MatchKnowledgeBase", fake)


def test_test_match_maps_auto_tier(monkeypatch) -> None:
    _fake_match_knowledge_base(
        monkeypatch,
        result=MatchResult(
            MatchTier.AUTO,
            hit=KbHit(document_id=7, topic="Общежитие", answer="Заселение с 1 сентября", score=0.91),
        ),
    )
    app = _app(BotInstance(id=1, slug="bot-1", name="Бот"))

    response = TestClient(app).post("/kb/test-match", json={"text": "когда заселение"})

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "auto"
    assert body["hit"] == {
        "document_id": 7,
        "topic": "Общежитие",
        "content": "Заселение с 1 сентября",
        "score": 0.91,
    }
    assert body["candidates"] is None


def test_test_match_maps_candidates_tier(monkeypatch) -> None:
    _fake_match_knowledge_base(
        monkeypatch,
        result=MatchResult(
            MatchTier.CANDIDATES,
            candidates=[
                KbCandidate(document_id=1, topic="Общежитие", score=0.6),
                KbCandidate(document_id=2, topic="Стипендия", score=0.58),
            ],
        ),
    )
    app = _app(BotInstance(id=1, slug="bot-1", name="Бот"))

    response = TestClient(app).post("/kb/test-match", json={"text": "расскажите про общагу"})

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "candidates"
    assert body["hit"] is None
    assert [c["document_id"] for c in body["candidates"]] == [1, 2]


def test_test_match_maps_no_match_tier_with_explanatory_note(monkeypatch) -> None:
    _fake_match_knowledge_base(monkeypatch, result=MatchResult(MatchTier.NO_MATCH))
    app = _app(BotInstance(id=1, slug="bot-1", name="Бот"))

    response = TestClient(app).post("/kb/test-match", json={"text": "нечто не по теме"})

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "no_match"
    assert body["hit"] is None
    assert body["candidates"] is None
    assert body["note"]


def test_test_match_always_scopes_to_the_resolved_bot(monkeypatch) -> None:
    """The request body carries no bot/document id at all -- the use case is only
    ever called with the server-resolved bot's own id, never anything the client
    could supply, which is what rules out a cross-tenant lookup structurally."""
    seen: dict[str, object] = {}
    _fake_match_knowledge_base(monkeypatch, result=MatchResult(MatchTier.SKIP), seen=seen)
    bot = BotInstance(
        id=42,
        slug="bot-42",
        name="Бот 42",
        settings={"knowledge_base": {"auto_answer_threshold": 0.6}},
    )
    app = _app(bot)

    response = TestClient(app).post("/kb/test-match", json={"text": "тест"})

    assert response.status_code == 200
    assert seen["bot_instance_id"] == 42
    assert seen["text"] == "тест"
    assert seen["overrides"]["auto_answer_threshold"] == 0.6
    assert seen["overrides"]["candidate_min_threshold"] is None
