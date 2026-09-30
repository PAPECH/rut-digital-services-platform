from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....models.enums import AdminRoleEnum
from ...admins.infrastructure.models import Admin
from ..domain.staff_access import BotStaffAccess, StaffIdentity, StaffPermissions
from .models import AdminBotAccessRecord


def _permissions(record: AdminBotAccessRecord) -> StaffPermissions:
    return StaffPermissions(
        can_process_submissions=record.can_process_submissions,
        can_manage_content=record.can_manage_content,
        can_manage_forms=record.can_manage_forms,
        can_manage_staff=record.can_manage_staff,
        can_manage_maintenance=record.can_manage_maintenance,
        can_manage_capabilities=record.can_manage_capabilities,
        can_manage_campaigns=record.can_manage_campaigns,
        can_manage_form_tests=record.can_manage_form_tests,
    )


def _identity(record: Admin) -> StaffIdentity:
    return StaffIdentity(
        id=record.id,
        max_user_id=record.max_user_id,
        full_name=record.full_name,
        role=record.role.value,
        is_active=record.is_active,
    )


def _access(access: AdminBotAccessRecord, admin: Admin) -> BotStaffAccess:
    return BotStaffAccess(
        id=access.id,
        bot_instance_id=access.bot_instance_id,
        staff=_identity(admin),
        permissions=_permissions(access),
    )


class SqlAlchemyStaffAccessRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_bot(self, bot_instance_id: int) -> list[BotStaffAccess]:
        rows = self._session.execute(
            select(AdminBotAccessRecord, Admin)
            .join(Admin, Admin.id == AdminBotAccessRecord.admin_id)
            .where(AdminBotAccessRecord.bot_instance_id == bot_instance_id)
            .order_by(Admin.full_name, Admin.id)
        ).all()
        return [_access(access, admin) for access, admin in rows]

    def get(self, bot_instance_id: int, access_id: int) -> BotStaffAccess | None:
        row = self._session.execute(
            select(AdminBotAccessRecord, Admin)
            .join(Admin, Admin.id == AdminBotAccessRecord.admin_id)
            .where(
                AdminBotAccessRecord.id == access_id,
                AdminBotAccessRecord.bot_instance_id == bot_instance_id,
            )
        ).one_or_none()
        return _access(*row) if row else None

    def get_by_staff(self, bot_instance_id: int, staff_id: int) -> BotStaffAccess | None:
        row = self._session.execute(
            select(AdminBotAccessRecord, Admin)
            .join(Admin, Admin.id == AdminBotAccessRecord.admin_id)
            .where(
                AdminBotAccessRecord.admin_id == staff_id,
                AdminBotAccessRecord.bot_instance_id == bot_instance_id,
            )
        ).one_or_none()
        return _access(*row) if row else None

    def find_staff_by_max_user_id(self, max_user_id: str) -> StaffIdentity | None:
        record = self._session.execute(
            select(Admin).where(Admin.max_user_id == max_user_id.strip())
        ).scalar_one_or_none()
        return _identity(record) if record else None

    def add_staff(self, staff: StaffIdentity) -> StaffIdentity:
        record = Admin(
            max_user_id=staff.max_user_id,
            full_name=staff.full_name,
            role=AdminRoleEnum(staff.role),
            is_active=staff.is_active,
        )
        self._session.add(record)
        self._session.flush()
        return _identity(record)

    def add_access(
        self,
        bot_instance_id: int,
        staff_id: int,
        permissions: StaffPermissions,
    ) -> BotStaffAccess:
        record = AdminBotAccessRecord(
            admin_id=staff_id,
            bot_instance_id=bot_instance_id,
            **asdict(permissions),
        )
        self._session.add(record)
        self._session.flush()
        admin = self._session.get(Admin, staff_id)
        if admin is None:
            raise RuntimeError("Staff identity disappeared")
        return _access(record, admin)

    def update_permissions(
        self,
        access: BotStaffAccess,
        permissions: StaffPermissions,
    ) -> BotStaffAccess:
        if access.id is None:
            raise ValueError("Cannot update access without an ID")
        record = self._session.get(AdminBotAccessRecord, access.id)
        if record is None or record.bot_instance_id != access.bot_instance_id:
            raise LookupError(access.id)
        for key in StaffPermissions.__dataclass_fields__:
            setattr(record, key, getattr(permissions, key))
        self._session.flush()
        admin = self._session.get(Admin, record.admin_id)
        if admin is None:
            raise RuntimeError("Staff identity disappeared")
        return _access(record, admin)

    def delete(self, access: BotStaffAccess) -> None:
        if access.id is None:
            raise ValueError("Cannot delete access without an ID")
        record = self._session.get(AdminBotAccessRecord, access.id)
        if record is None or record.bot_instance_id != access.bot_instance_id:
            raise LookupError(access.id)
        self._session.delete(record)
