from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class SharedProfile:
    user_id: int
    external_user_id: str
    provider: str
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    email: str | None = None
    birth_date: date | None = None
    job_title: str | None = None
    structural_unit: str | None = None
    shared_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BotMembership:
    id: int | None
    bot_instance_id: int
    user_id: int
    is_active: bool = True
    local_data: dict[str, Any] = field(default_factory=dict)
    ban_chat: bool = False
    ban_chat_reason: str | None = None
    ban_forms: bool = False
    ban_forms_reason: str | None = None
    ban_app: bool = False
    ban_app_reason: str | None = None
    source_campaign_link_id: int | None = None
