from __future__ import annotations

from app.core.config import settings
from app.modules.knowledge_base.application.use_cases import MatchKnowledgeBase
from app.modules.knowledge_base.domain.entities import (
    MatchTier,
    MessageAiClassificationEnum,
    ScoredDocument,
    classify,
    passage_text,
)


class _FakeRepository:
    def __init__(self, scored: list[ScoredDocument]) -> None:
        self._scored = scored

    def find_nearest(self, _bot_instance_id: int, _query_vector: list[float], _limit: int):
        return self._scored


class _FakeEmbedder:
    def __init__(self, vector: list[float] | None) -> None:
        self._vector = vector

    def embed(self, _text: str) -> list[float] | None:
        return self._vector

    def warm_up(self) -> None:
        pass


def _match(scored: list[ScoredDocument], text: str, *, vector: list[float] | None = [0.0], **overrides):
    use_case = MatchKnowledgeBase(_FakeRepository(scored), _FakeEmbedder(vector))
    return use_case.execute(1, text, **overrides)


def test_find_answer_skips_when_provider_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "off")
    result = _match([], "когда будет готова справка")
    assert result.tier == MatchTier.SKIP


def test_find_answer_skips_on_empty_text() -> None:
    result = _match([], "   ")
    assert result.tier == MatchTier.SKIP


def test_find_answer_escalates_on_explicit_human_request(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    result = _match([], "позовите оператора пожалуйста")
    assert result.tier == MatchTier.ESCALATE


def test_find_answer_skips_when_embedding_model_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    result = _match([], "когда будет готова справка", vector=None)
    assert result.tier == MatchTier.SKIP


def test_find_answer_auto_answers_above_threshold(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    scored = [ScoredDocument(id=1, topic="Справка", content="Готова за 3 дня", score=0.95)]
    result = _match(scored, "когда будет готова справка")
    assert result.tier == MatchTier.AUTO
    assert result.hit is not None
    assert result.hit.document_id == 1
    assert result.hit.answer == "Готова за 3 дня"


def test_find_answer_offers_candidates_when_top_two_are_too_close(monkeypatch) -> None:
    # Task 089: оба выше порога автоответа, но почти равны — угадывать нельзя,
    # показываем оба варианта (реальный случай «есть ли льготы на общежитие»).
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    monkeypatch.setattr(settings, "KB_AUTO_ANSWER_MIN_MARGIN", 0.05)
    scored = [
        ScoredDocument(id=41, topic="Как оплатить проживание?", content="...", score=0.82),
        ScoredDocument(id=23, topic="Какие льготные категории есть?", content="...", score=0.81),
    ]
    result = _match(scored, "есть ли льготы на общежитие")
    assert result.tier == MatchTier.CANDIDATES
    assert [c.document_id for c in result.candidates] == [41, 23]


def test_find_answer_auto_answers_when_winner_is_clear(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    monkeypatch.setattr(settings, "KB_AUTO_ANSWER_MIN_MARGIN", 0.05)
    scored = [
        ScoredDocument(id=33, topic="Как заселиться в семейную комнату?", content="...", score=0.87),
        ScoredDocument(id=34, topic="Как переселиться в другую комнату?", content="...", score=0.60),
    ]
    result = _match(scored, "Могу ли я получить семейную комнату?")
    assert result.tier == MatchTier.AUTO
    assert result.hit is not None
    assert result.hit.document_id == 33


def test_find_answer_offers_ranked_candidates_in_medium_band(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    scored = [
        ScoredDocument(id=1, topic="Общежитие", content="...", score=0.65),
        ScoredDocument(id=2, topic="Стипендия", content="...", score=0.60),
    ]
    result = _match(scored, "расскажите про общагу")
    assert result.tier == MatchTier.CANDIDATES
    assert [c.document_id for c in result.candidates] == [1, 2]
    assert result.candidates[0].score > result.candidates[1].score


def test_find_answer_no_match_below_candidate_threshold(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    scored = [ScoredDocument(id=1, topic="Общежитие", content="...", score=0.1)]
    result = _match(scored, "совершенно не по теме")
    assert result.tier == MatchTier.NO_MATCH


def test_find_answer_no_match_when_kb_empty(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    result = _match([], "любой вопрос")
    assert result.tier == MatchTier.NO_MATCH


def test_find_answer_uses_platform_default_thresholds_when_no_override(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    monkeypatch.setattr(settings, "KB_AUTO_ANSWER_THRESHOLD", 0.70)
    # score 0.65 is below the 0.70 platform default -> not auto-answered.
    scored = [ScoredDocument(id=1, topic="Справка", content="Готова за 3 дня", score=0.65)]
    result = _match(scored, "когда будет готова справка")
    assert result.tier != MatchTier.AUTO


def test_find_answer_per_bot_auto_threshold_override_lowers_bar(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    monkeypatch.setattr(settings, "KB_AUTO_ANSWER_THRESHOLD", 0.70)
    # Same 0.65 score the platform default would reject, but this bot's own override
    # (BotSettings.knowledge_base.auto_answer_threshold) accepts it.
    scored = [ScoredDocument(id=1, topic="Справка", content="Готова за 3 дня", score=0.65)]
    result = _match(scored, "когда будет готова справка", auto_answer_threshold=0.60)
    assert result.tier == MatchTier.AUTO
    assert result.hit is not None
    assert result.hit.document_id == 1


def test_find_answer_per_bot_candidate_threshold_override_is_stricter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "kb_semantic")
    monkeypatch.setattr(settings, "KB_AUTO_ANSWER_THRESHOLD", 0.99)
    monkeypatch.setattr(settings, "KB_CANDIDATE_MIN_THRESHOLD", 0.55)
    scored = [
        ScoredDocument(id=1, topic="Общежитие", content="...", score=0.65),
        ScoredDocument(id=2, topic="Стипендия", content="...", score=0.60),
    ]
    # A stricter per-bot candidate threshold (0.62) excludes the second, weaker row
    # that the platform default (0.55) would have kept.
    result = _match(scored, "расскажите про общагу", candidate_min_threshold=0.62)
    assert result.tier == MatchTier.CANDIDATES
    assert [c.document_id for c in result.candidates] == [1]


def test_passage_text_combines_topic_and_tags() -> None:
    text = passage_text("Справка", ["документ", "бумага"])
    assert "Справка" in text
    assert "документ" in text
    assert "бумага" in text


def test_passage_text_without_tags_is_just_the_topic() -> None:
    # Ответ/содержимое в эмбеддинг не входит (Task 089) — для FAQ-зеркала без тегов
    # вектор строится ровно по тексту вопроса.
    assert passage_text("  Как получить место в общежитии?  ", None) == "Как получить место в общежитии?"


def test_classify_returns_the_enum_member_for_each_topic() -> None:
    assert classify("") == MessageAiClassificationEnum.empty
    assert classify("нужна справка об обучении") == MessageAiClassificationEnum.certificate
    assert classify("когда придёт стипендия") == MessageAiClassificationEnum.payment
    assert classify("вопрос про общежитие") == MessageAiClassificationEnum.dorm
    assert classify("привет, как дела") == MessageAiClassificationEnum.general
