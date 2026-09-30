from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...bot_instances.domain.staff_access import StaffPermissions
from ..domain.entities import AdminInvite, InviteKind
from .models import AdminInviteRecord

_PERMISSION_KEYS = {field.name for field in fields(StaffPermissions)}


def _permissions(value: dict | None) -> StaffPermissions | None:
    if value is None:
        return None
    return StaffPermissions(**{key: bool(v) for key, v in value.items() if key in _PERMISSION_KEYS})


def _to_domain(record: AdminInviteRecord) -> AdminInvite:
    return AdminInvite(
        id=record.id,
        kind=record.kind,  # type: ignore[arg-type]
        bot_instance_id=record.bot_instance_id,
        full_name=record.full_name,
        staff_role=record.staff_role,  # type: ignore[arg-type]
        permissions=_permissions(record.permissions),
        max_uses=record.max_uses,
        used_count=record.used_count,
        expires_at=record.expires_at,
        created_by_admin_id=record.created_by_admin_id,
        created_at=record.created_at,
        revoked_at=record.revoked_at,
    )


class SqlAlchemyAdminInviteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, invite: AdminInvite, token_hash: str) -> AdminInvite:
        record = AdminInviteRecord(
            token_hash=token_hash,
            kind=invite.kind,
            bot_instance_id=invite.bot_instance_id,
            full_name=invite.full_name,
            staff_role=invite.staff_role,
            permissions=asdict(invite.permissions) if invite.permissions else None,
            max_uses=invite.max_uses,
            used_count=invite.used_count,
            expires_at=invite.expires_at,
            created_by_admin_id=invite.created_by_admin_id,
        )
        self._session.add(record)
        self._session.flush()
        return _to_domain(record)

    def list(self, kind: InviteKind, bot_instance_id: int | None) -> list[AdminInvite]:
        records = self._session.execute(
            select(AdminInviteRecord)
            .where(
                AdminInviteRecord.kind == kind,
                AdminInviteRecord.bot_instance_id.is_(None)
                if bot_instance_id is None
                else AdminInviteRecord.bot_instance_id == bot_instance_id,
            )
            .order_by(AdminInviteRecord.created_at.desc(), AdminInviteRecord.id.desc())
        ).scalars()
        return [_to_domain(record) for record in records]

    def get(
        self, invite_id: int, kind: InviteKind, bot_instance_id: int | None
    ) -> AdminInvite | None:
        record = self._session.get(AdminInviteRecord, invite_id)
        if record is None or record.kind != kind or record.bot_instance_id != bot_instance_id:
            return None
        return _to_domain(record)

    def get_by_token_hash_for_update(self, token_hash: str) -> AdminInvite | None:
        record = self._session.execute(
            select(AdminInviteRecord)
            .where(AdminInviteRecord.token_hash == token_hash)
            .with_for_update()
        ).scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    def increment_used(self, invite_id: int) -> AdminInvite:
        record = self._require(invite_id)
        record.used_count += 1
        self._session.flush()
        return _to_domain(record)

    def revoke(self, invite_id: int, revoked_at: datetime) -> AdminInvite:
        record = self._require(invite_id)
        record.revoked_at = revoked_at
        self._session.flush()
        return _to_domain(record)

    def _require(self, invite_id: int) -> AdminInviteRecord:
        record = self._session.get(AdminInviteRecord, invite_id)
        if record is None:
            raise LookupError(invite_id)
        return record
