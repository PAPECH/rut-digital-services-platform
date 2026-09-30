from html import escape


def kb_answer_for_bot(topic: str, answer: str) -> str:
    """Ответ из базы знаний для отправки в MAX: вопрос/тема жирным заголовком, чтобы
    пользователь сразу видел, на какой именно вопрос бот отвечает, и понял, если
    подобран не тот (Task 089). Бот шлёт в ParseMode.HTML (bot/app/main.py) — тема
    экранируется; ответ идёт как и раньше, без экранирования."""
    return f"<b>{escape(topic.strip())}</b>\n\n{answer}"


def kb_answer_for_history(topic: str, answer: str) -> str:
    """То же для исходящего Message.text — админка и история показывают его как простой
    текст (white-space: pre-wrap), поэтому без HTML-разметки."""
    return f"{topic.strip()}\n\n{answer}"
