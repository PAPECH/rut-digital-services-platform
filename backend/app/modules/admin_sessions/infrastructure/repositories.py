from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ....core.security import HmacPurpose, hmac_sign
from ..domain.entities import AdminRefreshSession
from .models import AdminRefreshSessionRecord


def _to_domain(record: AdminRefreshSessionRecord) -> AdminRefreshSession:
    return AdminRefreshSession(
        id=record.id,
        admin_id=record.admin_id,
        family_id=record.family_id,
        token_hash=record.token_hash,
        expires_at=record.expires_at,
        absolute_expires_at=record.absolute_expires_at,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
        replaced_by_id=record.replaced_by_id,
        user_agent=record.user_agent,
        ip=record.ip,
    )


class HmacRefreshTokenCodec:
    def generate(self) -> str:
        return secrets.token_urlsafe(48)

    def digest(self, raw_token: str) -> str:
        return hmac_sign(HmacPurpose.ADMIN_REFRESH_TOKEN, raw_token)


class SqlAlchemyAdminSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session: AdminRefreshSession) -> AdminRefreshSession:
        record = AdminRefreshSessionRecord(
            admin_id=session.admin_id,
            family_id=session.family_id,
            token_hash=session.token_hash,
            expires_at=session.expires_at,
            absolute_expires_at=session.absolute_expires_at,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
            revoked_at=session.revoked_at,
            replaced_by_id=session.replaced_by_id,
            user_agent=session.user_agent,
            ip=session.ip,
        )
        self._session.add(record)
        self._session.flush()
        return _to_domain(record)

    def get_by_hash(
        self,
        token_hash: str,
        *,
        for_update: bool = False,
    ) -> AdminRefreshSession | None:
        query = select(AdminRefreshSessionRecord).where(AdminRefreshSessionRecord.token_hash == token_hash)
        if for_update:
            query = query.with_for_update()
        record = self._session.execute(query).scalar_one_or_none()
        return _to_domain(record) if record else None

    def mark_rotated(
        self,
        session_id: int,
        *,
        replaced_by_id: int,
        used_at: datetime,
    ) -> None:
        self._session.execute(
            update(AdminRefreshSessionRecord)
            .where(AdminRefreshSessionRecord.id == session_id)
            .values(
                replaced_by_id=replaced_by_id,
                revoked_at=used_at,
                last_used_at=used_at,
            )
        )

    def revoke_family(self, family_id: str, *, revoked_at: datetime) -> None:
        self._session.execute(
            update(AdminRefreshSessionRecord)
            .where(
                AdminRefreshSessionRecord.family_id == family_id,
                AdminRefreshSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
