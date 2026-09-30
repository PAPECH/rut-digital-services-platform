from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .entities import AdminInvite, InviteKind


class AdminInviteRepository(Protocol):
    def add(self, invite: AdminInvite, token_hash: str) -> AdminInvite: ...

    def list(self, kind: InviteKind, bot_instance_id: int | None) -> list[AdminInvite]: ...

    def get(
        self, invite_id: int, kind: InviteKind, bot_instance_id: int | None
    ) -> AdminInvite | None: ...

    def get_by_token_hash_for_update(self, token_hash: str) -> AdminInvite | None: ...

    def increment_used(self, invite_id: int) -> AdminInvite: ...

    def revoke(self, invite_id: int, revoked_at: datetime) -> AdminInvite: ...
