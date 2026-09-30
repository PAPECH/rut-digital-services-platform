from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.entities import WEBAPP_CODE_MAX_LENGTH


class CampaignLinkCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=WEBAPP_CODE_MAX_LENGTH)
    campaign: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    placement: str = Field(min_length=1, max_length=200)
    target: Literal["bot", "webapp"]


class CampaignLinkResponse(BaseModel):
    id: int
    bot_instance_id: int
    code: str
    campaign: str
    source: str
    placement: str
    target: Literal["bot", "webapp"]
    created_at: datetime
    open_count: int
    unique_open_count: int
    # `first_open_count` mirrors `open_count` exactly (kept for backward compatibility, meaning
    # unchanged per link's target); `repeat_open_count` is new (Task 074) and stays 0 forever for
    # a `target: webapp` row, since that path's own counting is untouched by this task.
    first_open_count: int
    repeat_open_count: int
    last_opened_at: datetime | None
    bot_username: str | None
    deep_link: str


class UnmatchedCampaignLinkResponse(BaseModel):
    code: str
    event_source: Literal["bot_started", "bot_repeat", "webapp"]
    hit_count: int
    last_seen_at: datetime
