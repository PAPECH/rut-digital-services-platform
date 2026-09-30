from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditEntry:
    id: int
    created_at: datetime
    admin_id: int | None
    admin_name: str | None
    method: str
    path: str
    status_code: int | None
    duration_ms: int | None
    meta: dict[str, Any] | None
