import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ....models.enums import SystemEnum
from ..application.dto import BotProfile


class ProfileResponse(BaseModel):
    id: int
    user_id: str
    system: SystemEnum
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    username: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    email: str | None = None
    photo_url: str | None = None
    language_code: str | None = None
    birth_date: date | None = None
    study_group: str | None = None
    rut_personnel_number: str | None = None
    job_title: str | None = None
    structural_unit: str | None = None
    shared_data: dict[str, Any] = Field(default_factory=dict)
    local_data: dict[str, Any] = Field(default_factory=dict)
    ban_chat: bool = False
    ban_chat_reason: str | None = None
    ban_forms: bool = False
    ban_forms_reason: str | None = None
    ban_app: bool = False
    ban_app_reason: str | None = None
    # Task 064 -- drives the mini-app's full-screen consent gate exactly like ban_app does
    # for a ban: App.tsx gates on `!consent_is_active` right next to the ban_app check.
    # Populated from modules/consent, not from `record`/User -- see from_profile below.
    consent_is_active: bool = True
    consent_given_at: datetime | None = None
    consent_revoked_at: datetime | None = None
    consent_deletion_due_at: datetime | None = None
    consent_policy_url: str = ""

    @classmethod
    def from_profile(
        cls, value: BotProfile, record: Any, consent: Any = None, *, policy_url: str = ""
    ) -> "ProfileResponse":
        membership_fields = {
            "local_data",
            "ban_chat",
            "ban_chat_reason",
            "ban_forms",
            "ban_forms_reason",
            "ban_app",
            "ban_app_reason",
        }
        consent_fields = {
            "consent_is_active",
            "consent_given_at",
            "consent_revoked_at",
            "consent_deletion_due_at",
            "consent_policy_url",
        }
        return cls(
            **{
                key: getattr(record, key)
                for key in cls.model_fields
                if key not in membership_fields and key not in consent_fields and hasattr(record, key)
            },
            local_data=value.membership.local_data,
            ban_chat=value.membership.ban_chat,
            ban_chat_reason=value.membership.ban_chat_reason,
            ban_forms=value.membership.ban_forms,
            ban_forms_reason=value.membership.ban_forms_reason,
            ban_app=value.membership.ban_app,
            ban_app_reason=value.membership.ban_app_reason,
            consent_is_active=consent.is_active if consent is not None else False,
            consent_given_at=consent.given_at if consent is not None else None,
            consent_revoked_at=consent.revoked_at if consent is not None else None,
            consent_deletion_due_at=consent.deletion_due_at if consent is not None else None,
            consent_policy_url=policy_url,
        )


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=200)
    last_name: str | None = Field(default=None, max_length=200)
    patronymic: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    birth_date: date | None = None
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("first_name", "last_name", "patronymic", "email")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Некорректный адрес электронной почты")
        return value


class RutLinkResponse(BaseModel):
    status: str = "in_development"
    message: str = "Привязка табельного номера РУТ (МИИТ) пока в разработке."
