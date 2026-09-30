from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ....models.enums import SystemEnum


class InitDataIn(BaseModel):
    """Тело /auth/init-data/validate — строка initData с подписью + контур.

    Duplicated in `admin_sessions` rather than shared — see that module's copy for why.
    """

    init_data: str = Field(min_length=1, alias="initData")
    system: SystemEnum
    # Task 064: explicit affirmative act for the consent gate. When the resolved identity
    # has no active consent and this is false, the endpoint refuses to create/touch the
    # User row and answers with a `consent_required` error instead of a token. The gate
    # screen's "Я согласен" action re-calls this same endpoint with this set to true.
    accept_consent: bool = Field(default=False, alias="acceptConsent")

    model_config = {"populate_by_name": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_at: datetime


class StudentProfileOut(BaseModel):
    id: int
    user_id: str
    system: SystemEnum
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    username: str | None = None
    photo_url: str | None = None
    language_code: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    email: str | None = None
    birth_date: date | None = None
    study_group: str | None = None
    job_title: str | None = None
    structural_unit: str | None = None
    shared_data: dict[str, Any] = Field(default_factory=dict)
    ban_chat: bool = False
    ban_chat_reason: str | None = None
    ban_forms: bool = False
    ban_forms_reason: str | None = None
    ban_app: bool = False
    ban_app_reason: str | None = None

    model_config = {"from_attributes": True}


class StudentLoginOut(BaseModel):
    token: TokenOut
    user: StudentProfileOut


class ContactIn(BaseModel):
    phone: str
    auth_date: int = Field(alias="authDate")
    hash: str
    system: SystemEnum

    model_config = {"populate_by_name": True}


class ContactOut(BaseModel):
    ok: bool
    phone: str
    verified: bool = True
