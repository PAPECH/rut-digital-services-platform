from __future__ import annotations

from ...audit.infrastructure.models import AuditLog
from ..domain.entities import AdminInvite


def invite_audit_entry(
    *,
    action: str,
    invite: AdminInvite,
    actor_admin_id: int | None,
    method: str,
    path: str,
    status_code: int,
    extra: dict | None = None,
) -> AuditLog:
    return AuditLog(
        admin_id=actor_admin_id,
        bot_instance_id=invite.bot_instance_id,
        method=method,
        path=path,
        status_code=status_code,
        meta={
            "action": action,
            "invite_id": invite.id,
            "kind": invite.kind,
            **(extra or {}),
        },
    )
