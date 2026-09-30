from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.admin_account import AdminAccount, AdminRoleEnum
from .models import Admin


def _to_domain(record: Admin) -> AdminAccount:
    return AdminAccount(
        id=record.id,
        max_user_id=record.max_user_id,
        full_name=record.full_name,
        role=record.role.value,
        is_active=record.is_active,
    )


class SqlAlchemyAdminAccountRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[AdminAccount]:
        records = self._db.execute(select(Admin).order_by(Admin.created_at.desc())).scalars()
        return [_to_domain(record) for record in records]

    def find_by_max_user_id(self, max_user_id: str) -> AdminAccount | None:
        record = self._db.execute(
            select(Admin).where(Admin.max_user_id == max_user_id)
        ).scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    def get(self, admin_id: int) -> AdminAccount | None:
        record = self._db.get(Admin, admin_id)
        return _to_domain(record) if record is not None else None

    def add(self, account: AdminAccount) -> AdminAccount:
        record = Admin(
            max_user_id=account.max_user_id,
            full_name=account.full_name,
            role=AdminRoleEnum(account.role),
            is_active=account.is_active,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return _to_domain(record)

    def update(self, admin_id: int, changes: dict[str, object]) -> AdminAccount:
        record = self._db.get(Admin, admin_id)
        if record is None:
            raise LookupError(admin_id)
        for key, value in changes.items():
            setattr(record, key, value)
        self._db.commit()
        self._db.refresh(record)
        return _to_domain(record)

    def delete(self, admin_id: int) -> None:
        record = self._db.get(Admin, admin_id)
        if record is None:
            raise LookupError(admin_id)
        self._db.delete(record)
        self._db.commit()
