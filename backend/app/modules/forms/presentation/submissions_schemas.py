from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ....models.enums import SubmissionStatusEnum


class SubmissionIn(BaseModel):
    form_template_id: int
    form_version_id: int
    values: dict[str, Any] = Field(default_factory=dict)  # stable field key -> value
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=64)


class StatusHistoryOut(BaseModel):
    id: int
    from_status: SubmissionStatusEnum | None
    to_status: SubmissionStatusEnum
    changed_by: int | None
    changed_at: datetime
    comment: str | None = None

    model_config = {"from_attributes": True}


class SubmitterOut(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    username: str | None = None
    photo_url: str | None = None
    user_id: str | None = None
    system: str | None = None
    birth_date: date | None = None
    study_group: str | None = None
    phone: str | None = None
    phone_verified: bool = False
    email: str | None = None


class SubmissionOut(BaseModel):
    id: int
    form_template_id: int
    form_version_id: int
    user_id: int
    values: dict[str, Any]
    values_en: dict[str, Any] | None = None
    field_labels: dict[str, Any] = Field(default_factory=dict)
    form_snapshot: dict[str, Any] = Field(default_factory=dict)
    profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    status: SubmissionStatusEnum
    created_at: datetime
    taken_at: datetime | None = None
    closed_at: datetime | None = None
    assignee_admin_id: int | None = None

    model_config = {"from_attributes": True}


class AppointmentOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    location: str


class AppointmentSlotOut(BaseModel):
    starts_at: datetime
    submission_id: int


class AppointmentBookIn(BaseModel):
    slot_starts: list[datetime] = Field(min_length=1, max_length=2)


class SubmissionDetailed(SubmissionOut):
    history: list[StatusHistoryOut] = Field(default_factory=list)
    submitter: SubmitterOut | None = None
    form_name: str | None = None
    appointment: AppointmentOut | None = None


class SubmissionAttachmentOut(BaseModel):
    id: int
    field_key: str
    name: str
    mime: str
    size_bytes: int
    preview_url: str
    download_url: str


class StatusPatchIn(BaseModel):
    status: SubmissionStatusEnum
    comment: str | None = None
