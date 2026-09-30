from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field

from ..domain.staff_access import BotStaffAccess, StaffPermissions


class StaffPermissionsSchema(BaseModel):
    can_process_submissions: bool = True
    can_manage_content: bool = False
    can_manage_forms: bool = False
    can_manage_staff: bool = False
    can_manage_maintenance: bool = False
    can_manage_capabilities: bool = False
    can_manage_campaigns: bool = False
    can_manage_form_tests: bool = False

    def to_domain(self) -> StaffPermissions:
        return StaffPermissions(**self.model_dump())


class GrantStaffAccessRequest(BaseModel):
    max_user_id: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    role: Literal["employee", "admin"] = "employee"
    permissions: StaffPermissionsSchema = Field(default_factory=StaffPermissionsSchema)


class UpdateStaffAccessRequest(BaseModel):
    permissions: StaffPermissionsSchema


class StaffAccessResponse(BaseModel):
    id: int
    admin_id: int
    bot_instance_id: int
    max_user_id: str
    full_name: str
    role: Literal["employee", "admin", "platform_admin"]
    is_active: bool
    permissions: StaffPermissionsSchema

    @classmethod
    def from_domain(cls, access: BotStaffAccess) -> "StaffAccessResponse":
        if access.id is None or access.staff.id is None:
            raise ValueError("Staff access must be persisted")
        return cls(
            id=access.id,
            admin_id=access.staff.id,
            bot_instance_id=access.bot_instance_id,
            max_user_id=access.staff.max_user_id,
            full_name=access.staff.full_name,
            role=access.staff.role,
            is_active=access.staff.is_active,
            permissions=StaffPermissionsSchema(**asdict(access.permissions)),
        )
