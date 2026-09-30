from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RatingEntryResponse(BaseModel):
    plan_id: int
    specialty: str
    qualification: str
    points: float
    preference: str
    competition: str
    group_name: str
    position: int
    total: int
    checked_at: datetime


class RatingLookupResponse(BaseModel):
    applicant_code: str
    entries: list[RatingEntryResponse]
    is_subscribed: bool


class RatingSubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicant_code: str = Field(min_length=1, max_length=64)


class RatingSubscriptionResponse(BaseModel):
    applicant_code: str | None = None
    is_active: bool
