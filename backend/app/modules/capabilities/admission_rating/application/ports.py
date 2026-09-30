from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.config import AdmissionRatingConfig


@dataclass(frozen=True, slots=True)
class ProviderPlan:
    plan_id: int
    specialty: str
    qualification: str
    totals: dict[str, int]


@dataclass(frozen=True, slots=True)
class ProviderRating:
    plan_id: int
    applicant_code: str
    points: float
    preference: str
    competition: str
    group_name: str
    position: int


@dataclass(frozen=True, slots=True)
class AdmissionRatingSnapshot:
    plans: tuple[ProviderPlan, ...]
    ratings: tuple[ProviderRating, ...]


class AdmissionRatingProvider(Protocol):
    async def read_snapshot(self, config: AdmissionRatingConfig) -> AdmissionRatingSnapshot: ...

    async def probe(self, config: AdmissionRatingConfig) -> None: ...
