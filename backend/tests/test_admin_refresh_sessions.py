from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.admin_sessions.application.services import (
    RefreshReuseDetected,
    RotateAdminSession,
    StartAdminSession,
)
from app.modules.admin_sessions.domain.entities import AdminRefreshSession


class SequentialCodec:
    def __init__(self) -> None:
        self.counter = 0

    def generate(self) -> str:
        self.counter += 1
        return f"raw-token-{self.counter}"

    def digest(self, raw_token: str) -> str:
        return f"digest:{raw_token}"


class InMemorySessionRepository:
    def __init__(self) -> None:
        self.items: dict[int, AdminRefreshSession] = {}
        self.next_id = 1

    def add(self, session: AdminRefreshSession) -> AdminRefreshSession:
        stored = replace(session, id=self.next_id)
        self.items[self.next_id] = stored
        self.next_id += 1
        return stored

    def get_by_hash(
        self,
        token_hash: str,
        *,
        for_update: bool = False,
    ) -> AdminRefreshSession | None:
        del for_update
        return next((item for item in self.items.values() if item.token_hash == token_hash), None)

    def mark_rotated(
        self,
        session_id: int,
        *,
        replaced_by_id: int,
        used_at: datetime,
    ) -> None:
        self.items[session_id] = replace(
            self.items[session_id],
            replaced_by_id=replaced_by_id,
            revoked_at=used_at,
            last_used_at=used_at,
        )

    def revoke_family(self, family_id: str, *, revoked_at: datetime) -> None:
        for session_id, item in list(self.items.items()):
            if item.family_id == family_id and item.revoked_at is None:
                self.items[session_id] = replace(item, revoked_at=revoked_at)


def test_refresh_token_rotates_and_keeps_family_absolute_expiry() -> None:
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    repository = InMemorySessionRepository()
    codec = SequentialCodec()
    first = StartAdminSession(
        repository,
        codec,
        refresh_days=30,
        absolute_days=90,
    ).execute(7, user_agent="pytest", ip="127.0.0.1", now=now)

    second = RotateAdminSession(repository, codec, refresh_days=30).execute(
        first.raw_token,
        user_agent="pytest-2",
        ip="127.0.0.2",
        now=now + timedelta(days=1),
    )

    assert second.raw_token != first.raw_token
    assert second.session.family_id == first.session.family_id
    assert second.session.absolute_expires_at == first.session.absolute_expires_at
    assert repository.items[first.session.id].replaced_by_id == second.session.id
    assert repository.items[first.session.id].revoked_at == now + timedelta(days=1)


def test_reusing_rotated_token_revokes_whole_family() -> None:
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    repository = InMemorySessionRepository()
    codec = SequentialCodec()
    first = StartAdminSession(
        repository,
        codec,
        refresh_days=30,
        absolute_days=90,
    ).execute(7, user_agent=None, ip=None, now=now)
    RotateAdminSession(repository, codec, refresh_days=30).execute(
        first.raw_token,
        user_agent=None,
        ip=None,
        now=now + timedelta(minutes=1),
    )

    with pytest.raises(RefreshReuseDetected):
        RotateAdminSession(repository, codec, refresh_days=30).execute(
            first.raw_token,
            user_agent=None,
            ip=None,
            now=now + timedelta(minutes=2),
        )

    assert all(item.revoked_at is not None for item in repository.items.values())
