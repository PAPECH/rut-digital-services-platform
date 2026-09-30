from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ..domain.entities import AdminRefreshSession
from .ports import AdminSessionRepository, RefreshTokenCodec


class RefreshSessionInvalid(RuntimeError):
    pass


class RefreshSessionExpired(RuntimeError):
    pass


class RefreshReuseDetected(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IssuedRefreshSession:
    raw_token: str
    session: AdminRefreshSession


class StartAdminSession:
    def __init__(
        self,
        repository: AdminSessionRepository,
        codec: RefreshTokenCodec,
        *,
        refresh_days: int,
        absolute_days: int,
    ) -> None:
        self._repository = repository
        self._codec = codec
        self._refresh_days = refresh_days
        self._absolute_days = absolute_days

    def execute(
        self,
        admin_id: int,
        *,
        user_agent: str | None,
        ip: str | None,
        now: datetime | None = None,
    ) -> IssuedRefreshSession:
        issued_at = now or datetime.now(tz=timezone.utc)
        raw_token = self._codec.generate()
        absolute_expires_at = issued_at + timedelta(days=self._absolute_days)
        session = self._repository.add(
            AdminRefreshSession(
                id=None,
                admin_id=admin_id,
                family_id=str(uuid4()),
                token_hash=self._codec.digest(raw_token),
                expires_at=min(issued_at + timedelta(days=self._refresh_days), absolute_expires_at),
                absolute_expires_at=absolute_expires_at,
                created_at=issued_at,
                user_agent=user_agent,
                ip=ip,
            )
        )
        return IssuedRefreshSession(raw_token=raw_token, session=session)


class RotateAdminSession:
    def __init__(
        self,
        repository: AdminSessionRepository,
        codec: RefreshTokenCodec,
        *,
        refresh_days: int,
    ) -> None:
        self._repository = repository
        self._codec = codec
        self._refresh_days = refresh_days

    def execute(
        self,
        raw_token: str,
        *,
        user_agent: str | None,
        ip: str | None,
        now: datetime | None = None,
    ) -> IssuedRefreshSession:
        used_at = now or datetime.now(tz=timezone.utc)
        current = self._repository.get_by_hash(self._codec.digest(raw_token), for_update=True)
        if current is None:
            raise RefreshSessionInvalid
        if current.revoked_at is not None or current.was_rotated:
            self._repository.revoke_family(current.family_id, revoked_at=used_at)
            raise RefreshReuseDetected
        if current.is_expired(used_at):
            self._repository.revoke_family(current.family_id, revoked_at=used_at)
            raise RefreshSessionExpired
        successor_raw = self._codec.generate()
        successor = self._repository.add(
            AdminRefreshSession(
                id=None,
                admin_id=current.admin_id,
                family_id=current.family_id,
                token_hash=self._codec.digest(successor_raw),
                expires_at=min(
                    used_at + timedelta(days=self._refresh_days),
                    current.absolute_expires_at,
                ),
                absolute_expires_at=current.absolute_expires_at,
                created_at=used_at,
                user_agent=user_agent,
                ip=ip,
            )
        )
        if current.id is None or successor.id is None:
            raise RuntimeError("Refresh session persistence did not return IDs")
        self._repository.mark_rotated(
            current.id,
            replaced_by_id=successor.id,
            used_at=used_at,
        )
        return IssuedRefreshSession(raw_token=successor_raw, session=successor)


class RevokeAdminSession:
    def __init__(self, repository: AdminSessionRepository, codec: RefreshTokenCodec) -> None:
        self._repository = repository
        self._codec = codec

    def execute(self, raw_token: str, *, now: datetime | None = None) -> None:
        revoked_at = now or datetime.now(tz=timezone.utc)
        current = self._repository.get_by_hash(self._codec.digest(raw_token), for_update=True)
        if current is not None:
            self._repository.revoke_family(current.family_id, revoked_at=revoked_at)
