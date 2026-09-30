from __future__ import annotations

from typing import Protocol

from ..domain.entities import AdminRefreshSession


class RefreshTokenCodec(Protocol):
    def generate(self) -> str: ...

    def digest(self, raw_token: str) -> str: ...


class AdminSessionRepository(Protocol):
    def add(self, session: AdminRefreshSession) -> AdminRefreshSession: ...

    def get_by_hash(self, token_hash: str, *, for_update: bool = False) -> AdminRefreshSession | None: ...

    def mark_rotated(
        self,
        session_id: int,
        *,
        replaced_by_id: int,
        used_at,
    ) -> None: ...

    def revoke_family(self, family_id: str, *, revoked_at) -> None: ...
