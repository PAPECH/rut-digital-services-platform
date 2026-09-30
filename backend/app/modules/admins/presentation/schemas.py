from __future__ import annotations

from pydantic import BaseModel

from ..domain.admin_account import AdminAccount, AdminRoleEnum


class AdminOut(BaseModel):
    id: int
    max_user_id: str
    full_name: str
    role: AdminRoleEnum
    is_active: bool

    @classmethod
    def from_domain(cls, account: AdminAccount) -> "AdminOut":
        if account.id is None:
            raise ValueError("Admin account must be persisted")
        return cls(
            id=account.id,
            max_user_id=account.max_user_id,
            full_name=account.full_name,
            role=AdminRoleEnum(account.role),
            is_active=account.is_active,
        )


class AdminCreateIn(BaseModel):
    max_user_id: str
    full_name: str
    role: AdminRoleEnum = AdminRoleEnum.employee
    is_active: bool = True


class AdminPatchIn(BaseModel):
    full_name: str | None = None
    role: AdminRoleEnum | None = None
    is_active: bool | None = None
