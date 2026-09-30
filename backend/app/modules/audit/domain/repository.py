from __future__ import annotations

from typing import Protocol

from .entities import AuditEntry


class AuditLogRepository(Protocol):
    def list_for_bot(self, bot_instance_id: int, *, limit: int, offset: int) -> list[AuditEntry]: ...
