from datetime import date, datetime

from pydantic import BaseModel

from ....models.enums import SystemEnum


class CampaignSourceOut(BaseModel):
    """First-touch campaign-link attribution (Task 026) — read-only, set once at membership
    creation, never on later opens."""

    code: str
    campaign: str
    source: str
    placement: str
    target: str


class UserSummary(BaseModel):
    id: int
    user_id: str
    system: SystemEnum
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    username: str | None = None
    photo_url: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    email: str | None = None
    birth_date: date | None = None
    study_group: str | None = None
    job_title: str | None = None
    structural_unit: str | None = None
    ban_chat: bool = False
    ban_chat_reason: str | None = None
    ban_forms: bool = False
    ban_forms_reason: str | None = None
    ban_app: bool = False
    ban_app_reason: str | None = None
    created_at: datetime
    campaign_source: CampaignSourceOut | None = None
    # Task 064 -- read-only, same permission as the rest of this card. Null revoked_at with
    # a set given_at means active consent; a set revoked_at means pending deletion on
    # consent_deletion_due_at (the member card still exists only up to that point -- after
    # the sweep runs, the row is gone and this stops applying).
    consent_given_at: datetime | None = None
    consent_revoked_at: datetime | None = None
    consent_deletion_due_at: datetime | None = None

    model_config = {"from_attributes": True}


class BanPatchIn(BaseModel):
    """Управление блокировками — только админ."""

    ban_chat: bool | None = None
    ban_chat_reason: str | None = None
    ban_forms: bool | None = None
    ban_forms_reason: str | None = None
    ban_app: bool | None = None
    ban_app_reason: str | None = None
