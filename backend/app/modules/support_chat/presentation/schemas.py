from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from ....models.enums import MessageDirectionEnum, SystemEnum


class AttachmentOut(BaseModel):
    url: str
    name: str | None = None
    mime: str | None = None
    size: int | None = None


class MessageOut(BaseModel):
    id: int
    user_id: int
    system: SystemEnum
    direction: MessageDirectionEnum
    text: str | None = None
    attachments: list[AttachmentOut] | None = None
    is_ai_answered: bool = False
    ai_classification: str | None = None
    kb_document_id: int | None = None
    replied_by_admin_id: int | None = None
    replied_by_admin_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngressMessageIn(BaseModel):
    user_id: str  # external (MAX) user_id
    system: SystemEnum
    text: str | None = None
    attachments: list[dict[str, Any]] | None = None
    external_id: str | None = None  # для идемпотентности
    language_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class KbCandidateOut(BaseModel):
    document_ref: int
    topic: str


class IngressMessageOut(BaseModel):
    # None только когда chat_disabled=true — короткое замыкание ничего не пишет в БД,
    # поэтому и вернуть сохранённое incoming-сообщение не может.
    message: MessageOut | None = None
    answer: str | None = None  # уверенный прямой ответ AI
    candidates: list[KbCandidateOut] | None = None  # несколько вариантов — показать кнопками
    candidates_prompt: str | None = None  # текст-заголовок над кнопками candidates
    no_match_prompt: str | None = None  # «ничего не найдено» + кнопка «позвать сотрудника»
    # id этого incoming-сообщения — опорная точка для callback-кнопок
    # (candidates/no_match_prompt). Не задаётся, если кнопки не нужны.
    message_ref: str | None = None
    # true — у бота выключен приём свободного текста (BotSettings.chat), ничего не
    # сохранено и не обработано; адаптер должен показать тот же редирект, что и /start.
    chat_disabled: bool = False
    # true — личность без активного согласия (Task 064): ни User, ни Message не созданы,
    # текст не обработан. Адаптер должен показать экран/промпт согласия вместо ошибки.
    consent_required: bool = False
    # Заполняется только вместе с consent_required=True — чтобы бот не делал второй
    # запрос за ссылкой на политику.
    consent_policy_url: str | None = None


class AiCallbackIn(BaseModel):
    user_id: str  # external (MAX) user_id
    system: SystemEnum
    message_ref: str
    action: Literal["select", "call_staff"]
    document_ref: int | None = None  # обязателен для action="select"


class AiCallbackOut(BaseModel):
    text: str


class StaffReplyIn(BaseModel):
    text: str | None = None
    mark_as_read: bool = False
    # Список id вложений из POST /api/files. Перед отправкой backend заполнит url/name/mime/size.
    attachment_ids: list[int] | None = None
    attachments: list[dict[str, Any]] | None = None  # альтернативный вариант — внешние ссылки


class StudentMessageIn(BaseModel):
    """Сообщение от mini-app студента — если решим открыть отдельный экран чата."""

    text: str | None = None
    attachment_ids: list[int] | None = None
    attachments: list[dict[str, Any]] | None = None


class TicketsOverview(BaseModel):
    open_count: int
    unread_count: int


class ConversationItem(BaseModel):
    user_id: int
    max_user_id: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    system: SystemEnum
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    has_open_ticket: bool = False
    is_favorite: bool = False
    my_favorite: bool = False
    # true — открытый тикет появился из явного запроса человека (кнопка «Позвать
    # сотрудника» или совпадение по ключевым словам в тексте), см. ai_classification
    # "kb_staff_requested"/"kb_staff_requested_text" в messages.py.
    staff_requested: bool = False


class StaffFavoriteIn(BaseModel):
    user_id: int
    is_favorite: bool
