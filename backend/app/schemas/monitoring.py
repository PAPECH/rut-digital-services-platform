from datetime import datetime

from pydantic import BaseModel


class LookupOut(BaseModel):
    request_number: str
    status: str | None = None
    checked_at: datetime | None = None
    is_subscribed: bool = False


class SubscriptionOut(BaseModel):
    request_number: str | None = None
    is_active: bool = False
    last_status: str | None = None
    checked_at: datetime | None = None


class SubscribeIn(BaseModel):
    request_number: str


class SubscribeOut(BaseModel):
    request_number: str
    is_active: bool
