from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RatingEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: int
    display_name: str
    spec_display_name: str  # добавили
    spec_qualifier: str
    points: float
    preference_index_display: str
    competition_name: str
    group_name: str
    rating_index: int
    checked_at: datetime | None = None
    total: int


class RatingLookupOut(BaseModel):
    display_name: str
    entries: list[RatingEntryOut]
    is_subscribed: bool


class RatingSubscribeIn(BaseModel):
    display_name: str


class RatingSubscribeOut(BaseModel):
    display_name: str
    is_active: bool


class RatingSubscriptionOut(BaseModel):
    display_name: str | None = None
    is_active: bool
    entries: list[RatingEntryOut] = []
