from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, get_current_principal, require_staff, require_student
from ....core.errors import bad_request, forbidden, not_found, unauthorized
from ....db.redis import redis_client
from ....db.session import get_db
from ....models.attachment import Attachment
from ....models.enums import MessageDirectionEnum
from ....services.bot_runtime_auth import authorize_bot_runtime
from ....services.bot_settings import student_text_enabled
from ....services.files import make_signed_url
from ....services.push import enqueue_push
from ....services.rate_limit import enforce_rate_limit, max_user_rate_identity, rate_limit
from ....services.ws_hub import hub, staff_room, user_room
from ...admins.infrastructure.models import Admin
from ...bot_instances.domain.entities import BotInstance
from ...knowledge_base.application.settings import kb_overrides
from ...knowledge_base.application.use_cases import MatchKnowledgeBase
from ...knowledge_base.domain.entities import MatchTier, MessageAiClassificationEnum, classify
from ...knowledge_base.infrastructure.embedding import FastEmbedEmbeddingPort
from ...knowledge_base.infrastructure.models import KbDocumentRecord
from ...knowledge_base.infrastructure.repositories import SqlAlchemyKbDocumentRepository
from ...consent.application.use_cases import CheckConsentGate
from ...consent.infrastructure.funnel import ConsentFunnelEvent, bump_consent_funnel
from ...consent.infrastructure.notice_repository import effective_policy_url
from ...consent.infrastructure.repositories import SqlAlchemyConsentRepository
from ...maintenance.presentation.dependencies import enforce_user_write_available
from ...profiles.application.services import EnsureBotMembership
from ...profiles.infrastructure.gateways import SqlAlchemyProfileGateway
from ...profiles.infrastructure.models import BotMembershipRecord, User
from ...tenancy.presentation.dependencies import require_tenant_access, resolve_tenant
from ..infrastructure.models import Message
from .kb_answer_text import kb_answer_for_bot, kb_answer_for_history
from .message_render import (
    _STAFF_CALLBACK_CONFIRMATION,
    _STAFF_CALLBACK_CONFIRMATION_EN,
    _render_match,
)
from .schemas import (
    AiCallbackIn,
    AiCallbackOut,
    IngressMessageIn,
    IngressMessageOut,
    MessageOut,
    StaffReplyIn,
    StudentMessageIn,
)

_ALREADY_HANDLED = "Уже обработано."

_student_msg_rl = rate_limit("student_msg", limit=20, window_seconds=60)
_staff_msg_rl = rate_limit("staff_msg", limit=120, window_seconds=60)

log = logging.getLogger(__name__)

router = APIRouter()


def _resolve_attachments(
    db: Session,
    bot_instance_id: int,
    attachment_ids: list[int] | None,
    external_attachments: list[dict] | None,
) -> list[dict] | None:
    out: list[dict] = []
    if attachment_ids:
        rows = db.execute(
            select(Attachment).where(
                Attachment.id.in_(attachment_ids),
                Attachment.bot_instance_id == bot_instance_id,
            )
        ).scalars().all()
        if {row.id for row in rows} != set(attachment_ids):
            raise forbidden("Вложение принадлежит другому боту", code="cross_tenant_attachment")
        for a in rows:
            out.append(
                {
                    "id": a.id,
                    "url": make_signed_url(a.id),
                    "name": a.original_name,
                    "mime": a.mime,
                    "size": a.size_bytes,
                }
            )
    if external_attachments:
        for ext in external_attachments:
            if ext and ext.get("url"):
                out.append(ext)
    return out or None


def _get_or_create_user_from_external(db: Session, payload: IngressMessageIn) -> User:
    user = db.execute(
        select(User).where(User.user_id == payload.user_id, User.system == payload.system)
    ).scalar_one_or_none()
    if user is None:
        user = User(
            user_id=payload.user_id,
            system=payload.system,
            first_name=payload.first_name,
            last_name=payload.last_name,
            username=payload.username,
            language_code=payload.language_code or "ru",
        )
        db.add(user)
        db.flush()
    else:
        if payload.first_name and not user.first_name:
            user.first_name = payload.first_name
        if payload.last_name and not user.last_name:
            user.last_name = payload.last_name
        if payload.username and not user.username:
            user.username = payload.username
        if payload.language_code:
            user.language_code = payload.language_code
    return user


@router.post(
    "/ingress",
    response_model=IngressMessageOut,
)
async def ingress_message(
    payload: IngressMessageIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> IngressMessageOut:
    if bot.id is None:
        raise not_found("Бот не найден", code="bot_not_found")
    authorize_bot_runtime(db, bot.id, x_bot_runtime_token, x_bot_token)
    enforce_rate_limit(
        "msg_ingress",
        limit=600,
        window_seconds=60,
        tenant=bot.slug,
        identity=max_user_rate_identity(payload.system.value, payload.user_id),
    )

    if not student_text_enabled(bot.settings):
        # Бот настроен не принимать свободный текст (BotSettings.chat) — короткое
        # замыкание до идемпотентности/пользователя/матчинга/согласия: ничего не
        # читается и не пишется в БД, ни тикета, ни сообщения не появляется. Адаптер
        # (bot/app/main.py) на chat_disabled=true покажет тот же редирект, что и по
        # /start. Checked before the consent gate deliberately -- a channel that's
        # closed regardless doesn't need a consent lookup to reach that same "nothing
        # happens" outcome.
        return IngressMessageOut(chat_disabled=True)

    # Consent gate (Task 064): no User row created/refilled, no message stored, no
    # content routed to staff/AI. This is exactly the hazard docs/tasks/064 calls out for
    # `_get_or_create_user_from_external` below (it silently refills empty PII fields on
    # an existing row), so the gate must sit in front of it, not just at initial signup.
    if not CheckConsentGate(SqlAlchemyConsentRepository(db)).execute(
        payload.user_id, payload.system.value
    ):
        bump_consent_funnel(db, bot.id, ConsentFunnelEvent.gate_shown)
        db.commit()
        return IngressMessageOut(
            consent_required=True, consent_policy_url=effective_policy_url()
        )

    # Идемпотентность
    if payload.external_id:
        existing = db.execute(
            select(Message).where(
                Message.bot_instance_id == bot.id,
                Message.external_id == payload.external_id,
            )
        ).scalar_one_or_none()
        if existing:
            return IngressMessageOut(message=MessageOut.model_validate(existing, from_attributes=True))

    user = _get_or_create_user_from_external(db, payload)
    membership = EnsureBotMembership(SqlAlchemyProfileGateway(db)).execute(bot.id, user.id)
    if not membership.is_active:
        raise forbidden("Доступ к этому боту отключён", code="membership_inactive")
    if membership.ban_app:
        raise forbidden(membership.ban_app_reason or "Доступ к приложению заблокирован", code="ban_app")
    if membership.ban_chat:
        raise forbidden(membership.ban_chat_reason or "Чат заблокирован", code="ban_chat")

    classification = classify(payload.text or "")
    # Матчинг гоняет CPU-bound инференс эмбеддинга — не блокировать event loop.
    match_use_case = MatchKnowledgeBase(SqlAlchemyKbDocumentRepository(db), FastEmbedEmbeddingPort())
    match = await asyncio.to_thread(
        match_use_case.execute, bot.id, payload.text or "", **kb_overrides(bot.settings)
    )
    en = _is_en(user.language_code)

    if match.tier == MatchTier.ESCALATE:
        # Реальный текст студента, а не синтетический маркер — рендерится как
        # обычное сообщение (ChatBubble во frontend-admin), но помечен отдельным
        # значением (не "kb_staff_requested" — тот зарезервирован за маркером из
        # ai_callback/call_staff, который НЕ настоящий пользовательский текст), чтобы
        # ConversationItem.staff_requested (tickets_router.py) видел явный запрос человека
        # и через текстовый путь, не только через кнопку.
        classification = MessageAiClassificationEnum.kb_staff_requested_text

    incoming = Message(
        bot_instance_id=bot.id,
        user_id=user.id,
        system=payload.system,
        direction=MessageDirectionEnum.in_,
        text=payload.text,
        attachments=payload.attachments,
        is_ai_answered=match.tier == MatchTier.AUTO,
        ai_classification=classification,
        external_id=payload.external_id,
    )
    db.add(incoming)
    db.flush()

    rendered = _render_match(match, en)
    message_ref = str(incoming.id) if match.tier in (MatchTier.CANDIDATES, MatchTier.NO_MATCH) else None

    outgoing: Message | None = None
    if rendered.outgoing_text is not None:
        outgoing = Message(
            bot_instance_id=bot.id,
            user_id=user.id,
            system=payload.system,
            direction=MessageDirectionEnum.out,
            text=rendered.outgoing_text,
            is_ai_answered=rendered.outgoing_is_ai_answered,
            ai_classification=rendered.outgoing_classification,
            kb_document_id=rendered.outgoing_kb_document_id,
        )
        db.add(outgoing)
        db.flush()

    db.commit()
    db.refresh(incoming)
    if outgoing is not None:
        db.refresh(outgoing)

    in_dto = MessageOut.model_validate(incoming, from_attributes=True).model_dump(mode="json")
    await hub.broadcast(user_room(user.id, bot.id), {"type": "message", "data": in_dto})
    if outgoing is None:
        await hub.broadcast(
            staff_room(bot.id),
            {"type": "new_ticket", "user_id": user.id, "data": in_dto},
        )
    else:
        out_dto = MessageOut.model_validate(outgoing, from_attributes=True).model_dump(mode="json")
        await hub.broadcast(user_room(user.id, bot.id), {"type": "message", "data": out_dto})
    # ESCALATE больше не создаёт outgoing (см. _render_match) — стафф уже получил
    # new_ticket выше, в ветке "outgoing is None", ровно как при SKIP.

    return IngressMessageOut(
        message=MessageOut.model_validate(incoming, from_attributes=True),
        answer=rendered.answer,
        candidates=rendered.candidates,
        candidates_prompt=rendered.candidates_prompt,
        no_match_prompt=rendered.no_match_prompt,
        message_ref=message_ref,
    )


def _is_en(language_code: str | None) -> bool:
    lc = (language_code or "").lower()
    return bool(lc) and not lc.startswith("ru")


@router.post(
    "/ai/callback",
    response_model=AiCallbackOut,
)
async def ai_callback(
    payload: AiCallbackIn,
    bot: BotInstance = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    x_bot_token: str | None = Header(default=None, alias="X-Bot-Token"),
    x_bot_runtime_token: str | None = Header(default=None, alias="X-Bot-Runtime-Token"),
) -> AiCallbackOut:
    """Резолвит нажатие кнопки под сообщением-кандидатами/«ничего не найдено».

    message_ref — id исходного incoming Message (см. IngressMessageOut.message_ref),
    не документ и не бот — идентичность бота/тенанта и владельца сообщения
    перепроверяются здесь, а не берутся из payload кнопки.
    """
    if bot.id is None:
        raise not_found("Бот не найден", code="bot_not_found")
    authorize_bot_runtime(db, bot.id, x_bot_runtime_token, x_bot_token)
    enforce_rate_limit(
        "msg_ai_callback",
        limit=120,
        window_seconds=60,
        tenant=bot.slug,
        identity=max_user_rate_identity(payload.system.value, payload.user_id),
    )

    try:
        message_id = int(payload.message_ref)
    except ValueError:
        raise bad_request("Некорректный message_ref", code="invalid_message_ref") from None

    user = db.execute(
        select(User).where(User.user_id == payload.user_id, User.system == payload.system)
    ).scalar_one_or_none()
    if user is None:
        raise forbidden("Сообщение принадлежит другому пользователю", code="cross_tenant_ai_callback")

    incoming = db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.bot_instance_id == bot.id,
            Message.user_id == user.id,
            Message.direction == MessageDirectionEnum.in_,
        )
    ).scalar_one_or_none()
    if incoming is None:
        raise forbidden("Сообщение принадлежит другому пользователю или боту", code="cross_tenant_ai_callback")

    idempotency_key = f"kb-callback-resolved:{bot.id}:{incoming.id}"
    if not redis_client.set(idempotency_key, "1", nx=True, ex=3600):
        return AiCallbackOut(text=_ALREADY_HANDLED)

    en = _is_en(user.language_code)

    if payload.action == "call_staff":
        # Подтверждение студент видит на MAX-стороне через редактирование исходного
        # сообщения-подсказки callback-ответом (адаптер: on_ai_callback в
        # bot/app/main.py) — оно НЕ логируется здесь ещё одним outgoing-сообщением:
        # has_open_ticket (tickets_router.py) выводится из "последнее входящее позже
        # последнего исходящего" — залогируй мы исходящее подтверждение ПОСЛЕ
        # маркера ниже, тикет тут же перестал бы выглядеть открытым для стаффа.
        marker = Message(
            bot_instance_id=bot.id,
            user_id=user.id,
            system=payload.system,
            direction=MessageDirectionEnum.in_,
            text="[Пользователь запросил помощь сотрудника]",
            is_ai_answered=False,
            ai_classification=MessageAiClassificationEnum.kb_staff_requested,
        )
        db.add(marker)
        db.commit()
        db.refresh(marker)
        marker_dto = MessageOut.model_validate(marker, from_attributes=True).model_dump(mode="json")
        await hub.broadcast(
            staff_room(bot.id),
            {"type": "new_ticket", "user_id": user.id, "data": marker_dto},
        )
        return AiCallbackOut(
            text=_STAFF_CALLBACK_CONFIRMATION_EN if en else _STAFF_CALLBACK_CONFIRMATION
        )

    if payload.document_ref is None:
        raise bad_request("document_ref обязателен для action=select", code="missing_document_ref")
    document = db.execute(
        select(KbDocumentRecord).where(
            KbDocumentRecord.id == payload.document_ref,
            KbDocumentRecord.bot_instance_id == bot.id,
            KbDocumentRecord.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if document is None:
        raise not_found("Документ недоступен", code="kb_document_unavailable")

    incoming.is_ai_answered = True
    outgoing = Message(
        bot_instance_id=bot.id,
        user_id=user.id,
        system=payload.system,
        direction=MessageDirectionEnum.out,
        text=kb_answer_for_history(document.topic, document.content),
        is_ai_answered=True,
        ai_classification=MessageAiClassificationEnum.kb_selected,
        kb_document_id=document.id,
    )
    db.add(outgoing)
    db.commit()
    db.refresh(outgoing)

    out_dto = MessageOut.model_validate(outgoing, from_attributes=True).model_dump(mode="json")
    await hub.broadcast(user_room(user.id, bot.id), {"type": "message", "data": out_dto})

    return AiCallbackOut(text=kb_answer_for_bot(document.topic, document.content))


@router.get("", response_model=list[MessageOut])
def list_messages(
    user_id: int = Query(...),
    limit: int = Query(default=300, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(get_current_principal),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[Message]:
    if p.role == "student" and p.user_id != user_id:
        raise forbidden("Чужая переписка")
    q = (
        select(Message)
        .where(Message.bot_instance_id == bot.id, Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(q).scalars())[::-1]


@router.post(
    "/to-user/{user_pk}",
    response_model=MessageOut,
    dependencies=[Depends(_staff_msg_rl)],
)
async def staff_reply(
    user_pk: int,
    payload: StaffReplyIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_staff),
    bot: BotInstance = Depends(require_tenant_access),
) -> Message:
    attachments = _resolve_attachments(db, bot.id, payload.attachment_ids, payload.attachments)
    if not payload.text and not attachments:
        raise bad_request("Пустое сообщение")
    user = db.get(User, user_pk)
    if user is None:
        raise not_found("Пользователь не найден")
    membership = db.execute(
        select(BotMembershipRecord.id).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == user.id,
            BotMembershipRecord.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if membership is None:
        raise not_found("Пользователь не найден в выбранном боте")

    msg = Message(
        bot_instance_id=bot.id,
        user_id=user.id,
        system=user.system,
        direction=MessageDirectionEnum.out,
        text=payload.text,
        attachments=attachments,
        replied_by_admin_id=p.admin_id,
    )
    admin = db.get(Admin, p.admin_id) if p.admin_id else None
    if not payload.mark_as_read:
        enqueue_push(
            db,
            bot_instance_id=bot.id,
            user_id=user.id,
            kind="staff_message",
            payload={
                "text": payload.text or "",
                "admin_name": admin.full_name if admin else None,
                "attachments": attachments or [],
            },
        )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    dto = MessageOut.model_validate(msg, from_attributes=True).model_dump(mode="json")

    await hub.broadcast(user_room(user.id, bot.id), {"type": "message", "data": dto})

    await hub.broadcast(staff_room(bot.id), {"type": "ticket_answered", "user_id": user.id})

    return msg


# Сообщение от студента (на случай если будет отдельный экран чата в mini-app)
@router.post(
    "/from-student",
    response_model=MessageOut,
    dependencies=[Depends(_student_msg_rl), Depends(enforce_user_write_available)],
)
async def student_message(
    payload: StudentMessageIn,
    db: Session = Depends(get_db),
    p: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
) -> Message:
    user = db.get(User, p.user_id)
    if user is None:
        raise unauthorized("Студент не найден")
    membership = db.execute(
        select(BotMembershipRecord).where(
            BotMembershipRecord.bot_instance_id == bot.id,
            BotMembershipRecord.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None or not membership.is_active:
        raise forbidden("Доступ к этому боту отключён", code="membership_inactive")
    if membership.ban_app:
        raise forbidden(membership.ban_app_reason or "Доступ к приложению заблокирован", code="ban_app")
    if membership.ban_chat:
        raise forbidden(membership.ban_chat_reason or "Чат заблокирован", code="ban_chat")

    attachments = _resolve_attachments(db, bot.id, payload.attachment_ids, payload.attachments)
    if not payload.text and not attachments:
        raise bad_request("Пустое сообщение")

    msg = Message(
        bot_instance_id=bot.id,
        user_id=user.id,
        system=user.system,
        direction=MessageDirectionEnum.in_,
        text=payload.text,
        attachments=attachments,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    dto = MessageOut.model_validate(msg, from_attributes=True).model_dump(mode="json")
    await hub.broadcast(user_room(user.id, bot.id), {"type": "message", "data": dto})
    await hub.broadcast(
        staff_room(bot.id),
        {"type": "new_ticket", "user_id": user.id, "data": dto},
    )
    return msg
