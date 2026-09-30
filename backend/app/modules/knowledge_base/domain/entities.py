from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

# Студент явно просит человека — пропускаем сопоставление и сразу эскалируем,
# не заставляя его ещё и нажимать кнопку за то, о чём он уже попросил текстом.
_HUMAN_REQUEST_RE = re.compile(
    r"(оператор|специалист[а-я]*|сотрудник[а-я]*|человек[а-я]*|поддержк[а-я]*|"
    r"соедини[а-я]*|свяжи[а-я]*|позови[а-я]*|перезвони[а-я]*|"
    r"\boperator\b|\bhuman\b|\bsupport\b|\bagent\b)",
    re.IGNORECASE,
)


def is_explicit_human_request(text: str) -> bool:
    return bool(_HUMAN_REQUEST_RE.search(text.lower()))


def passage_text(topic: str, tags: list[str] | None) -> str:
    """Текст, который эмбеддится для документа: тема (для FAQ-зеркала — сам вопрос) +
    ключевые слова. Содержимое/ответ намеренно не входит: пользователь задаёт вопрос,
    а не пересказывает ответ, и длинный ответ «размывал» вектор так, что даже дословный
    вопрос из FAQ не находил собственную запись (docs/tasks/089-kb-match-by-question.md).
    Меняешь состав этого текста — добавь миграцию, обнуляющую kb_documents.embedding,
    иначе старые векторы останутся в прежнем формате."""
    parts = [topic.strip()]
    if tags:
        parts.append(" ".join(t.strip() for t in tags if t and t.strip()))
    return "\n".join(p for p in parts if p)


class MessageAiClassificationEnum(StrEnum):
    """Единый словарь значений Message.ai_classification — раньше это была
    произвольная строка, в которую независимо писали classify() (тема входящего
    сообщения) и KB-пайплайн (_render_match/ai_callback в api/routes/messages.py,
    состояние исходящего). id документа больше не зашивается в строку
    (kb:{id}/kb_selected:{id}) — см. Message.kb_document_id."""

    # Темы входящего сообщения — classify() ниже
    empty = "empty"
    certificate = "certificate"
    payment = "payment"
    dorm = "dorm"
    general = "general"
    # Явный запрос человека через текст (перезаписывает тему выше) — ingress_message
    kb_staff_requested_text = "kb_staff_requested_text"
    # Состояние KB-пайплайна на исходящем сообщении
    kb_auto = "kb_auto"
    kb_candidates = "kb_candidates"
    kb_no_match = "kb_no_match"
    kb_staff_requested = "kb_staff_requested"
    kb_selected = "kb_selected"
    # Значение из cli/import_legacy.py, не сопоставившееся ни с одним из вышеперечисленных
    legacy_unknown = "legacy_unknown"


# Значения, при которых открытый тикет считается результатом явного запроса
# человека (кнопка или текст) — общий источник для tickets.py и frontend-admin,
# чтобы не дублировать список в двух местах.
STAFF_REQUESTED_CLASSIFICATIONS = frozenset(
    {
        MessageAiClassificationEnum.kb_staff_requested,
        MessageAiClassificationEnum.kb_staff_requested_text,
    }
)


def classify(text: str) -> MessageAiClassificationEnum:
    """Очень грубая классификация для UI/аналитики."""
    if not text:
        return MessageAiClassificationEnum.empty
    t = text.lower()
    if any(k in t for k in ("справк", "документ", "certificate")):
        return MessageAiClassificationEnum.certificate
    if any(k in t for k in ("стипенди", "оплат", "плат", "scholarship")):
        return MessageAiClassificationEnum.payment
    if any(k in t for k in ("общежит", "dorm")):
        return MessageAiClassificationEnum.dorm
    return MessageAiClassificationEnum.general


@dataclass(frozen=True, slots=True)
class KbDocument:
    id: int | None
    bot_instance_id: int
    topic: str
    content: str
    tags: list[str] | None = None
    is_active: bool = True
    uploaded_by: int | None = None
    created_at: datetime | None = None
    # Не-null только для зеркал, автосозданных из KbFaq (Task 052) — источник
    # правды тогда /faq, а не этот документ напрямую (см. presentation/router.py).
    source_faq_id: int | None = None


@dataclass(frozen=True, slots=True)
class KbFaq:
    id: int | None
    bot_instance_id: int
    question: str
    answer: str
    is_active: bool = True
    order: int = 0


class MatchTier(StrEnum):
    AUTO = "auto"  # уверенный единственный ответ
    CANDIDATES = "candidates"  # несколько правдоподобных вариантов
    NO_MATCH = "no_match"  # ничего достаточно близкого не нашлось
    ESCALATE = "escalate"  # пользователь явно просит человека
    SKIP = "skip"  # матчинг не выполнялся (провайдер выключен/пустой текст/модель недоступна)


@dataclass(frozen=True, slots=True)
class KbHit:
    document_id: int
    topic: str
    answer: str
    score: float


@dataclass(frozen=True, slots=True)
class KbCandidate:
    document_id: int
    topic: str
    score: float


@dataclass(frozen=True, slots=True)
class MatchResult:
    tier: MatchTier
    hit: KbHit | None = None
    candidates: list[KbCandidate] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ScoredDocument:
    """Один кандидат из репозитория: id/topic/content документа + его cosine-similarity
    (1 - distance) к запросу. Внутренняя проекция матчинга, отдельная от KbDocument —
    репозиторий никогда не возвращает вектор эмбеддинга наружу."""

    id: int
    topic: str
    content: str
    score: float


def decide_tier(
    scored: list[ScoredDocument],
    *,
    auto_answer_threshold: float,
    candidate_min_threshold: float,
    auto_answer_min_margin: float = 0.0,
) -> MatchResult:
    """Чистое правило принятия решения по уже найденным и отсортированным (по убыванию
    score) кандидатам — не трогает БД/эмбеддинг-модель, поэтому тривиально тестируется
    без моков.

    Автоответ — только если лучший документ и выше порога, и обгоняет второй минимум на
    auto_answer_min_margin; иначе (два почти равных) — варианты на выбор."""
    if not scored:
        return MatchResult(MatchTier.NO_MATCH)

    best = scored[0]
    runner_up_score = scored[1].score if len(scored) > 1 else None
    clear_winner = runner_up_score is None or best.score - runner_up_score >= auto_answer_min_margin
    if best.score >= auto_answer_threshold and clear_winner:
        return MatchResult(
            MatchTier.AUTO,
            hit=KbHit(document_id=best.id, topic=best.topic, answer=best.content, score=best.score),
        )

    candidates = [
        KbCandidate(document_id=doc.id, topic=doc.topic, score=doc.score)
        for doc in scored
        if doc.score >= candidate_min_threshold
    ]
    if candidates:
        return MatchResult(MatchTier.CANDIDATES, candidates=candidates)

    return MatchResult(MatchTier.NO_MATCH)
