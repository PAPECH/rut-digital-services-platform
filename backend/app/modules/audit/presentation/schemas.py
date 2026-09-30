from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ..domain.entities import AuditEntry


class AuditEntryOut(BaseModel):
    id: int
    created_at: datetime
    admin_id: int | None
    admin_name: str | None
    method: str
    path: str
    status_code: int | None
    duration_ms: int | None
    meta: dict[str, Any] | None

    @classmethod
    def from_domain(cls, entry: AuditEntry) -> "AuditEntryOut":
        return cls(
            id=entry.id,
            created_at=entry.created_at,
            admin_id=entry.admin_id,
            admin_name=entry.admin_name,
            method=entry.method,
            path=entry.path,
            status_code=entry.status_code,
            duration_ms=entry.duration_ms,
            meta=entry.meta,
        )
