from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestStatusLookupResponse(StrictModel):
    request_number: str
    status: str | None
    checked_at: datetime | None
    is_subscribed: bool


class RequestStatusSubscriptionRequest(StrictModel):
    request_number: str = Field(min_length=1, max_length=64)


class RequestStatusSubscriptionResponse(StrictModel):
    request_number: str | None = None
    is_active: bool
    last_status: str | None = None
    checked_at: datetime | None = None
