"""WebSocket-чат (§8.3 ТЗ). Подписки на комнаты:

- staff — все сотрудники (новые тикеты, бейдж счётчика)
- user:<id> — конкретный разговор (студент + сотрудник)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ....core.security import decode_token
from ....db.session import SessionLocal
from ....services.ws_hub import hub, platform_admin_room, staff_room, user_room
from ...bot_instances.infrastructure.models import AdminBotAccessRecord, BotInstanceRecord
from ...profiles.infrastructure.models import BotMembershipRecord

log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def ws_chat(  # noqa: PLR0912
    websocket: WebSocket,
    token: str = Query(...),
    user_pk: int | None = Query(default=None),
    bot_slug: str | None = Query(default=None),
) -> None:
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    role = payload.get("role")
    student_pk = payload.get("user_pk")
    token_bot_id = payload.get("bot_instance_id")
    rooms: list[str] = []

    if role == "student":
        if not student_pk or not token_bot_id:
            await websocket.close(code=4401)
            return
        with SessionLocal() as db:
            membership = db.execute(
                select(BotMembershipRecord).where(
                    BotMembershipRecord.bot_instance_id == int(token_bot_id),
                    BotMembershipRecord.user_id == int(student_pk),
                )
            ).scalar_one_or_none()
            if membership is None or not membership.is_active or membership.ban_app:
                await websocket.close(code=4403)
                return
        rooms.append(user_room(int(student_pk), int(token_bot_id)))
    elif role in ("admin", "employee", "platform_admin"):
        if not bot_slug:
            await websocket.close(code=4403)
            return
        with SessionLocal() as db:
            bot = db.execute(
                select(BotInstanceRecord).where(
                    BotInstanceRecord.slug == bot_slug.strip().lower(),
                    BotInstanceRecord.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if bot is None:
                await websocket.close(code=4403)
                return
            if role != "platform_admin":
                admin_id = payload.get("admin_id")
                access = db.execute(
                    select(AdminBotAccessRecord.id).where(
                        AdminBotAccessRecord.admin_id == admin_id,
                        AdminBotAccessRecord.bot_instance_id == bot.id,
                    )
                ).scalar_one_or_none()
                if access is None:
                    await websocket.close(code=4403)
                    return
            if user_pk:
                membership = db.execute(
                    select(BotMembershipRecord.id).where(
                        BotMembershipRecord.bot_instance_id == bot.id,
                        BotMembershipRecord.user_id == int(user_pk),
                    )
                ).scalar_one_or_none()
                if membership is None:
                    await websocket.close(code=4403)
                    return
        rooms.append(staff_room(bot.id))
        if role == "platform_admin":
            # Operational events no bot admin may see (e.g. rut_schedule manual-sync updates) --
            # see ws_hub.platform_admin_room. Enforced here at join time, not left to the
            # frontend simply not rendering them for a lower-privileged connection.
            rooms.append(platform_admin_room(bot.id))
        if user_pk:
            rooms.append(user_room(int(user_pk), bot.id))
    else:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    for r in rooms:
        await hub.join(r, websocket)
    try:
        await websocket.send_json({"type": "ready", "rooms": rooms})
        while True:
            # Сейчас сервер не принимает входящие — отправка идёт через REST.
            # Просто держим соединение, отбрасывая входящие.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        for r in rooms:
            await hub.leave(r, websocket)
