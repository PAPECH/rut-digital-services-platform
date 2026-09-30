from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....models.enums import AdminRoleEnum
from ...admins.infrastructure.models import Admin
from ..domain.entities import GlobalAdminIdentity


def _identity(record: Admin) -> GlobalAdminIdentity:
    return GlobalAdminIdentity(
        id=record.id,
        max_user_id=record.max_user_id,
        full_name=record.full_name,
        role=record.role.value,
        is_active=record.is_active,
    )


class SqlAlchemyPlatformAdminRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_max_user_id(self, max_user_id: str) -> GlobalAdminIdentity | None:
        record = self._session.execute(
            select(Admin).where(Admin.max_user_id == max_user_id.strip())
        ).scalar_one_or_none()
        return _identity(record) if record is not None else None

    def list_platform_admins(self) -> list[GlobalAdminIdentity]:
        records = self._session.execute(
            select(Admin)
            .where(Admin.role == AdminRoleEnum.platform_admin)
            .order_by(Admin.is_active.desc(), Admin.full_name, Admin.id)
        ).scalars()
        return [_identity(record) for record in records]

    def add(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        record = Admin(
            max_user_id=identity.max_user_id,
            full_name=identity.full_name,
            role=AdminRoleEnum.platform_admin,
            is_active=True,
        )
        self._session.add(record)
        self._session.flush()
        return _identity(record)

    def update(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        if identity.id is None:
            raise ValueError("Cannot update an unpersisted administrator")
        record = self._session.get(Admin, identity.id)
        if record is None:
            raise LookupError(identity.id)
        record.full_name = identity.full_name
        record.role = AdminRoleEnum.platform_admin
        record.is_active = True
        self._session.flush()
        return _identity(record)
