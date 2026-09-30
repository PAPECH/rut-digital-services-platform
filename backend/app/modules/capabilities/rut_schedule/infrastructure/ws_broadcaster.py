from __future__ import annotations

from typing import Any

from .....services.ws_hub import hub, platform_admin_room

SYNC_UPDATE_EVENT_TYPE = "rut_schedule_sync_update"


class WsHubSyncEventBroadcaster:
    """Concrete `SyncEventBroadcaster` (see `application/ports.py`) over this platform's existing
    admin WebSocket hub -- not a new realtime subsystem, just one more room and event type on the
    `/ws/chat` hub Tickets/Submissions/UserCardPanel already use. See Task 045's Architecture."""

    async def broadcast(self, bot_instance_id: int, event: dict[str, Any]) -> None:
        await hub.broadcast(
            platform_admin_room(bot_instance_id),
            {"type": SYNC_UPDATE_EVENT_TYPE, "data": event},
        )
