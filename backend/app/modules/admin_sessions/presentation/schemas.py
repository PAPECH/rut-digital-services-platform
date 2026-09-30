from datetime import datetime

from pydantic import BaseModel, Field

from ....models.enums import AdminRoleEnum, SystemEnum


class InitDataIn(BaseModel):
    """Тело /auth/admin/login — строка initData с подписью + контур.

    Duplicated from `profiles`' identical schema rather than shared — both `/admin/login` and
    `/init-data/validate` need the exact same "signed MAX init-data envelope" shape, but the two
    modules stay independent (same reasoning as `TokenOut` below).
    """

    init_data: str = Field(min_length=1, alias="initData")
    system: SystemEnum

    model_config = {"populate_by_name": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_at: datetime


class AdminProfileOut(BaseModel):
    id: int
    max_user_id: str
    full_name: str
    role: AdminRoleEnum
    is_active: bool


class AdminLoginOut(BaseModel):
    token: TokenOut
    admin: AdminProfileOut
