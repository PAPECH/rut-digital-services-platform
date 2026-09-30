from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RatingEntry:
    plan_id: int
    applicant_code: str
    specialty: str
    qualification: str
    points: float
    preference: str
    competition: str
    group_name: str
    position: int
    total: int
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class RatingSubscription:
    id: int | None
    bot_instance_id: int
    installation_id: int
    user_id: int
    applicant_code: str
    applicant_code_hash: str
    is_active: bool
