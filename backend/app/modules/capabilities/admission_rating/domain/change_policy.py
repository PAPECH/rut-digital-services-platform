import re

_DATED_GROUP_SUFFIX = re.compile(r"\s*\d{2}\.\d{2}\.\d{4}$")
_COMPETITION_TITLES = {
    "ALL": "Всего мест",
    "BUDGET": "Бюджет",
    "CONCOURSE": "Общий конкурс",
    "SPECIAL_QUOTA": "Особая квота",
    "TARGET_QUOTA": "Целевая квота",
    "QUOTA_07": "Отдельная квота",
    "PAID": "Места по договорам",
}


def normalize_group_name(value: str) -> str:
    return _DATED_GROUP_SUFFIX.sub("", value.strip())


def competition_title(value: str) -> str:
    return _COMPETITION_TITLES.get(value, value)


def has_meaningful_rating_change(
    *,
    old_position: int,
    new_position: int,
    old_group: str,
    new_group: str,
    available_places: int,
) -> bool:
    group_changed = normalize_group_name(old_group) != normalize_group_name(new_group)
    position_changed_in_competition = (
        old_position != new_position and available_places > 0 and new_position <= available_places
    )
    return group_changed or position_changed_in_competition
