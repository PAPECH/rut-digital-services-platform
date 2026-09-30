"""Асинхронный клиент API приёмной комиссии МИИТ (планы приёма + рейтинг)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://miit.ru/api-1c/miit/hs/AdmissionPlan"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 YaBrowser/26.6.0.0 Safari/537.36"
    )
}

LEVELS = [
    {"value": "50", "display": "Высшее образование"},
    {"value": "60", "display": "Специализированное высшее образование (магистратура)"},
    {"value": "1", "display": "Среднее профессиональное образование (СПО)"},
    {"value": "3", "display": "Среднее профессиональное образование (на базе 9 классов)"},
    {"value": "2", "display": "Среднее профессиональное образование (на базе 11 классов)"},
    {"value": "8", "display": "Аспирантура"},
]

TRAININGS = [
    {"value": "20773", "display": "Очная"},
    {"value": "20775", "display": "Очно-заочная"},
    {"value": "20774", "display": "Заочная"},
]

COMPETITION_GROUPS = [
    {"type": "ALL", "title": "Всего мест", "field": "all_"},
    {"type": "BUDGET", "title": "Бюджет", "field": "budget"},
    {"type": "CONCOURSE", "title": "Общий конкурс", "field": "concourse"},
    {"type": "SPECIAL_QUOTA", "title": "Особая квота", "field": "special_quota"},
    {"type": "TARGET_QUOTA", "title": "Целевая квота", "field": "target_quota"},
    {"type": "QUOTA_07", "title": "Отдельная квота", "field": "quota_07"},
    {"type": "PAID", "title": "Места по договорам", "field": "paid"},
]

# для быстрого поиска: title -> имя поля в AdmissionPlan
TITLE_TO_FIELD = {item["title"]: item["field"] for item in COMPETITION_GROUPS}


_PLAN_ID_RE = re.compile(r"/(\d+)(?:\?|$)")


class MiitAdmissionError(Exception):
    pass


@dataclass
class PlanRow:
    plan_id: int
    plan_reception_url: str
    spec_display_name: str
    spec_qualifier: str
    all_: int
    budget: int
    concourse: int
    crimea: int
    paid: int
    paid_concourse: int
    paid_crimea: int
    quota_05: int
    quota_07: int
    special_quota: int
    target_quota: int
    level: str
    training: str


@dataclass
class RatingRowData:
    plan_id: int
    display_name: str
    points: float
    preference_index_display: str
    competition_name: str
    group_name: str
    rating_index: int


def _parse_points(value) -> float:
    """API отдаёт points то числом, то строкой с запятой как десятичным разделителем
    (например '4,889'), иногда пустой строкой. Нормализуем в float."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace(",", ".").replace(" ", "")
        if not normalized:
            return 0.0
        try:
            return float(normalized)
        except ValueError:
            log.warning("cannot parse points value: %r", value)
            return 0.0
    log.warning("unexpected points type: %r (%s)", value, type(value))
    return 0.0


async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise MiitAdmissionError(f"GET {url} failed: {e}") from e


def _extract_plan_id(url: str) -> int | None:
    m = _PLAN_ID_RE.search(url)
    return int(m.group(1)) if m else None


async def fetch_plan_data(client: httpx.AsyncClient, year: int, level: str, training: str) -> dict:
    url = f"{BASE_URL}/reception-plan?city=1&level={level}&year={year}&training={training}"
    return await _get_json(client, url)


def parse_plan_data(data: dict, level: str, training: str) -> list[PlanRow]:
    rows: list[PlanRow] = []
    if not data:
        return rows

    result = data.get("result") or [{}]
    for plan in result[0].get("concourseGroups", []):
        url = plan["planReceptionUrl"]
        plan_id = _extract_plan_id(url)
        if plan_id is None:
            log.warning("cannot extract plan_id from %s", url)
            continue

        nums = plan["planNumbers"]["integers"]
        rows.append(
            PlanRow(
                plan_id=plan_id,
                plan_reception_url=url,
                spec_display_name=plan["specDisplayName"],
                spec_qualifier=plan["specQualifier"],
                all_=nums["ALL"]["PLAN"] or 0,
                budget=nums["BUDGET"]["PLAN"] or 0,
                concourse=nums["CONCOURSE"]["PLAN"] or 0,
                crimea=nums["CRIMEA"]["PLAN"] or 0,
                paid=nums["PAID"]["PLAN"] or 0,
                paid_concourse=nums["PAID_CONCOURSE"]["PLAN"] or 0,
                paid_crimea=nums["PAID_CRIMEA"]["PLAN"] or 0,
                quota_05=nums["QUOTA_05"]["PLAN"] or 0,
                quota_07=nums["QUOTA_07"]["PLAN"] or 0,
                special_quota=nums["SPECIAL_QUOTA"]["PLAN"] or 0,
                target_quota=nums["TARGET_QUOTA"]["PLAN"] or 0,
                level=level,
                training=training,
            )
        )
    return rows


async def fetch_all_plans(client: httpx.AsyncClient, year: int) -> list[PlanRow]:
    rows: list[PlanRow] = []
    for level in LEVELS:
        for training in TRAININGS:
            data = await fetch_plan_data(client, year, level["value"], training["value"])
            rows.extend(parse_plan_data(data, level["value"], training["value"]))
    return rows


async def fetch_rating_data(client: httpx.AsyncClient, year: int, plan_id: int) -> dict:
    url = f"{BASE_URL}/rating?year={year}&id={plan_id}"
    return await _get_json(client, url)


def get_plan_total(plan: "AdmissionPlan", competition_name: str) -> int:
    """Возвращает кол-во мест в AdmissionPlan для конкретного конкурсного списка."""

    field = TITLE_TO_FIELD.get(competition_name)
    if field is None:
        return 0  # либо raise, если хотите жёстко валидировать
    return getattr(plan, field, 0)


def getGroupCompetition(type: str = None, title: str = None):
    if type is not None:
        find_by = "type"
        find_arg = type
    else:
        find_by = "title"
        find_arg = title
    return tuple(filter(lambda x: x[find_by] == find_arg, COMPETITION_GROUPS))[0]


def parse_rating_data(data: dict, plan_id: int) -> list[RatingRowData]:
    rows: list[RatingRowData] = []
    for competition in data.get("competitions", []):
        competition_name = getGroupCompetition(title=competition["competitionName"])["type"]

        unique_users = []

        for group in competition.get("projectEntrantGroups", []):
            group_name = group["name"]
            for entrant in group.get("entrants", []):
                if entrant.get("disabled") is True:
                    continue

                if entrant["displayName"] in unique_users:
                    continue

                unique_users.append(entrant["displayName"])

                rows.append(
                    RatingRowData(
                        plan_id=plan_id,
                        display_name=entrant["displayName"],
                        points=_parse_points(entrant["points"]),
                        preference_index_display=entrant["preferenceIndexDisplay"].strip(),
                        competition_name=competition_name,
                        group_name=group_name,
                        rating_index=entrant["ratingIndex"],
                    )
                )

        for group in competition.get("concourseEntrantGroups"):
            group_name = group["name"]
            for entrant in group.get("entrants", []):
                if entrant.get("disabled") is True:
                    continue

                if entrant["displayName"] in unique_users:
                    continue

                unique_users.append(entrant["displayName"])
                rows.append(
                    RatingRowData(
                        plan_id=plan_id,
                        display_name=entrant["displayName"],
                        points=_parse_points(entrant["points"]),
                        preference_index_display=entrant["preferenceIndexDisplay"].strip(),
                        competition_name=competition_name,
                        group_name=group_name,
                        rating_index=entrant["ratingIndex"],
                    )
                )

    return rows
