from ...knowledge_base.domain.entities import MatchTier, MessageAiClassificationEnum
from .kb_answer_text import kb_answer_for_bot, kb_answer_for_history
from .schemas import KbCandidateOut

_STAFF_CALLBACK_CONFIRMATION = "Ваше обращение отправлено сотруднику поддержки, мы ответим в этом чате."
_STAFF_CALLBACK_CONFIRMATION_EN = "Your request has been sent to support, we'll reply in this chat."
_NO_MATCH_PROMPT = "Ничего не найдено по вашему запросу. Нажмите кнопку, чтобы позвать сотрудника."
_NO_MATCH_PROMPT_EN = "Nothing found for your request. Tap the button to contact support."
_CANDIDATES_PROMPT = "Возможно, вы имели в виду один из вариантов ниже:"
_CANDIDATES_PROMPT_EN = "You might mean one of the options below:"


class _MatchRender:
    """Презентационная проекция MatchResult — что показать студенту и что записать
    в исходящее сообщение. Вынесено из ingress_message, чтобы не разрастались
    ветвления/тело функции."""

    __slots__ = (
        "answer",
        "candidates",
        "candidates_prompt",
        "no_match_prompt",
        "outgoing_text",
        "outgoing_is_ai_answered",
        "outgoing_classification",
        "outgoing_kb_document_id",
    )

    def __init__(
        self,
        *,
        answer: str | None = None,
        candidates: list[KbCandidateOut] | None = None,
        candidates_prompt: str | None = None,
        no_match_prompt: str | None = None,
        outgoing_text: str | None = None,
        outgoing_is_ai_answered: bool = False,
        outgoing_classification: MessageAiClassificationEnum | None = None,
        outgoing_kb_document_id: int | None = None,
    ) -> None:
        self.answer = answer
        self.candidates = candidates
        self.candidates_prompt = candidates_prompt
        self.no_match_prompt = no_match_prompt
        self.outgoing_text = outgoing_text
        self.outgoing_is_ai_answered = outgoing_is_ai_answered
        self.outgoing_classification = outgoing_classification
        self.outgoing_kb_document_id = outgoing_kb_document_id


def _render_match(match, en: bool) -> _MatchRender:
    if match.tier == MatchTier.AUTO:
        return _MatchRender(
            answer=kb_answer_for_bot(match.hit.topic, match.hit.answer),
            outgoing_text=kb_answer_for_history(match.hit.topic, match.hit.answer),
            outgoing_is_ai_answered=True,
            outgoing_classification=MessageAiClassificationEnum.kb_auto,
            outgoing_kb_document_id=match.hit.document_id,
        )
    if match.tier == MatchTier.CANDIDATES:
        prompt = _CANDIDATES_PROMPT_EN if en else _CANDIDATES_PROMPT
        return _MatchRender(
            candidates=[
                KbCandidateOut(document_ref=c.document_id, topic=c.topic) for c in match.candidates
            ],
            candidates_prompt=prompt,
            outgoing_text=prompt,
            outgoing_classification=MessageAiClassificationEnum.kb_candidates,
        )
    if match.tier == MatchTier.NO_MATCH:
        prompt = _NO_MATCH_PROMPT_EN if en else _NO_MATCH_PROMPT
        return _MatchRender(
            no_match_prompt=prompt,
            outgoing_text=prompt,
            outgoing_classification=MessageAiClassificationEnum.kb_no_match,
        )
    if match.tier == MatchTier.ESCALATE:
        # outgoing_text намеренно НЕ задан: как и в call_staff-ветке ai_callback,
        # подтверждение уходит студенту только транзитно (bot-адаптер отправит
        # rendered.answer живым сообщением в MAX), но не пишется исходящим Message —
        # иначе has_open_ticket (tickets_router.py, чисто по timestamp'ам) тут же увидел бы
        # исходящее позже входящего и посчитал бы тикет закрытым до того, как стафф
        # вообще увидел обращение в очереди.
        confirmation = _STAFF_CALLBACK_CONFIRMATION_EN if en else _STAFF_CALLBACK_CONFIRMATION
        return _MatchRender(answer=confirmation)
    # MatchTier.SKIP — outgoing не создаётся, как раньше: тихо падаем в очередь стаффа.
    return _MatchRender()
