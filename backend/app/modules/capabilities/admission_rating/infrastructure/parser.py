from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

LEVEL_IDS = ("50", "60", "1", "3", "2", "8")
TRAINING_IDS = ("20773", "20775", "20774")

_PLAN_ID_RE = re.compile(r"/(\d+)(?:\?|$)")
_COMPETITION_TYPES = {
    "Всего мест": "ALL",
    "Бюджет": "BUDGET",
    "Общий конкурс": "CONCOURSE",
    "Особая квота": "SPECIAL_QUOTA",
    "Целевая квота": "TARGET_QUOTA",
    "Отдельная квота": "QUOTA_07",
    "Места по договорам": "PAID",
}
_TOTAL_FIELDS = {
    "ALL": "ALL",
    "BUDGET": "BUDGET",
    "CONCOURSE": "CONCOURSE",
    "SPECIAL_QUOTA": "SPECIAL_QUOTA",
    "TARGET_QUOTA": "TARGET_QUOTA",
    "QUOTA_07": "QUOTA_07",
    "PAID": "PAID",
}


@dataclass(frozen=True, slots=True)
class ParsedPlan:
    plan_id: int
    specialty: str
    qualification: str
    totals: dict[str, int]


@dataclass(frozen=True, slots=True)
class ParsedRating:
    applicant_code: str
    points: float
    preference: str
    competition: str
    group_name: str
    position: int


def _points(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    if isinstance(value, bool):
        raise ValueError("invalid points")
    if isinstance(value, int | float):
        return float(value)
    return float(str(value).strip().replace(" ", "").replace(",", "."))


def parse_plans(payload: dict[str, Any]) -> list[ParsedPlan]:
    result = payload.get("result") or []
    if not isinstance(result, list) or not result:
        return []
    groups = result[0].get("concourseGroups", [])
    if not isinstance(groups, list):
        raise ValueError("invalid plan groups")
    parsed: list[ParsedPlan] = []
    for value in groups:
        match = _PLAN_ID_RE.search(str(value["planReceptionUrl"]))
        if match is None:
            continue
        integers = value["planNumbers"]["integers"]
        totals = {
            key: max(0, int((integers.get(source) or {}).get("PLAN") or 0))
            for key, source in _TOTAL_FIELDS.items()
        }
        parsed.append(
            ParsedPlan(
                plan_id=int(match.group(1)),
                specialty=str(value["specDisplayName"]).strip(),
                qualification=str(value["specQualifier"]).strip(),
                totals=totals,
            )
        )
    return parsed


def parse_ratings(payload: dict[str, Any]) -> list[ParsedRating]:
    competitions = payload.get("competitions", [])
    if not isinstance(competitions, list):
        raise ValueError("invalid competitions")
    parsed: list[ParsedRating] = []
    for competition in competitions:
        title = str(competition["competitionName"])
        competition_type = _COMPETITION_TYPES.get(title)
        if competition_type is None:
            continue
        seen: set[str] = set()
        groups = list(competition.get("projectEntrantGroups") or [])
        groups.extend(competition.get("concourseEntrantGroups") or [])
        for group in groups:
            group_name = str(group["name"]).strip()
            for entrant in group.get("entrants") or []:
                if entrant.get("disabled") is True:
                    continue
                applicant_code = str(entrant["displayName"])
                if applicant_code in seen:
                    continue
                seen.add(applicant_code)
                parsed.append(
                    ParsedRating(
                        applicant_code=applicant_code,
                        points=_points(entrant.get("points")),
                        preference=str(entrant.get("preferenceIndexDisplay") or "").strip(),
                        competition=competition_type,
                        group_name=group_name,
                        position=int(entrant["ratingIndex"]),
                    )
                )
    return parsed
