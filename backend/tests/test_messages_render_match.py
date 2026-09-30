"""_render_match — регрессия для бага «эскалация закрывает тикет» (Task 049).

Раньше MatchTier.ESCALATE (студент явно попросил человека текстом) заполнял
outgoing_text, из-за чего ingress_message писал подтверждение исходящим Message
сразу после входящего — has_open_ticket (tickets.py, чисто по timestamp'ам)
считал тикет закрытым до того, как стафф вообще увидел обращение. Кнопочный путь
(ai_callback/call_staff, см. test_ai_callback_http.py) уже не создавал outgoing —
этот файл проверяет, что текстовый путь теперь ведёт себя так же.
"""

from __future__ import annotations

from app.modules.support_chat.presentation.message_render import _render_match
from app.modules.knowledge_base.domain.entities import MatchResult, MatchTier


def test_escalate_does_not_set_outgoing_text_ru() -> None:
    rendered = _render_match(MatchResult(MatchTier.ESCALATE), en=False)
    assert rendered.outgoing_text is None
    assert rendered.answer is not None
    assert "поддержки" in rendered.answer


def test_escalate_does_not_set_outgoing_text_en() -> None:
    rendered = _render_match(MatchResult(MatchTier.ESCALATE), en=True)
    assert rendered.outgoing_text is None
    assert rendered.answer is not None
    assert "support" in rendered.answer.lower()


def test_skip_still_does_not_set_outgoing_text() -> None:
    # Регрессия: SKIP и раньше не создавал outgoing — не должно было измениться.
    rendered = _render_match(MatchResult(MatchTier.SKIP), en=False)
    assert rendered.outgoing_text is None
    assert rendered.answer is None


def test_auto_still_sets_outgoing_text() -> None:
    # Регрессия: не задели остальные тиры при правке ESCALATE-ветки.
    from app.modules.knowledge_base.domain.entities import KbHit

    match = MatchResult(
        MatchTier.AUTO,
        hit=KbHit(document_id=1, topic="Справка", answer="Готова за 3 дня", score=0.9),
    )
    rendered = _render_match(match, en=False)
    # Task 089: вопрос/тема заголовком — в MAX жирным (HTML), в истории простым текстом.
    assert rendered.answer == "<b>Справка</b>\n\nГотова за 3 дня"
    assert rendered.outgoing_text == "Справка\n\nГотова за 3 дня"
    assert rendered.outgoing_classification == "kb_auto"
    assert rendered.outgoing_kb_document_id == 1


def test_auto_answer_heading_escapes_html_in_topic() -> None:
    from app.modules.knowledge_base.domain.entities import KbHit

    match = MatchResult(
        MatchTier.AUTO,
        hit=KbHit(document_id=1, topic="Оплата <1 месяца & долг", answer="Ответ", score=0.9),
    )
    rendered = _render_match(match, en=False)
    assert rendered.answer == "<b>Оплата &lt;1 месяца &amp; долг</b>\n\nОтвет"
    assert rendered.outgoing_text == "Оплата <1 месяца & долг\n\nОтвет"
