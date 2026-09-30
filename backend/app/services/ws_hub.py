"""Простой in-memory hub для WebSocket-чата сотрудников и mini-app (§8.3 ТЗ).

Сообщения broadcast'ятся:
- staff-каналу (всем подключённым сотрудникам)
- комнате конкретного пользователя `user:<id>` (студент + сотрудник, открывшие диалог)
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger(__name__)


class WsHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].add(ws)

    async def leave(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].discard(ws)
            if not self._rooms[room]:
                self._rooms.pop(room, None)

    async def broadcast(self, room: str, event: dict) -> None:
        sockets: list[WebSocket]
        async with self._lock:
            sockets = list(self._rooms.get(room, ()))
        for ws in sockets:
            try:
                await ws.send_json(event)
            except Exception as e:
                log.debug("ws send failed: %s", e)


hub = WsHub()


def staff_room(bot_instance_id: int | None = None) -> str:
    return f"staff:bot:{bot_instance_id}" if bot_instance_id is not None else "staff"


def user_room(user_pk: int, bot_instance_id: int | None = None) -> str:
    return f"user:bot:{bot_instance_id}:{user_pk}" if bot_instance_id is not None else f"user:{user_pk}"


def platform_admin_room(bot_instance_id: int) -> str:
    """Platform-admin-only broadcast scope for a bot -- unlike `staff_room` (any staff/admin/
    platform_admin with access to the bot), only a `platform_admin` connection joins this. Used
    for operational events a bot admin must never receive (e.g. rut_schedule manual-sync updates),
    so the isolation is enforced at join time in `ws_chat`, not left to the frontend not
    rendering them. See docs/tasks/045-capabilities-admin-ux-and-rut-schedule-manual-sync.md."""
    return f"platform_admin:bot:{bot_instance_id}"
