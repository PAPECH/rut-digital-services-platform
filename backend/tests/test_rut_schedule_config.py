from __future__ import annotations

import pytest

from app.modules.capabilities.rut_schedule.domain.config import (
    InvalidRutScheduleConfig,
    parse_rut_schedule_config,
)

_BASE = {
    "provider": "miit_timetable",
    "title": "Расписание",
    "subtitle": "Введите номер группы",
    "group_cache_ttl_seconds": 900,
    "hierarchy_sync_interval_seconds": 21_600,
}


def test_night_auto_sync_enabled_defaults_to_true_when_absent() -> None:
    """Task 045: installations configured before this field existed have a stored config JSON
    that simply lacks it -- it must not be treated as a "Missing fields" rejection, unlike every
    other key, or every such installation's browse view and nightly sync would start failing the
    moment this ships."""
    config = parse_rut_schedule_config(dict(_BASE))
    assert config.night_auto_sync_enabled is True
    # And it round-trips explicitly from here on, self-healing the stored row on next save.
    assert config.to_dict()["night_auto_sync_enabled"] is True


def test_night_auto_sync_enabled_explicit_value_is_honored() -> None:
    config = parse_rut_schedule_config({**_BASE, "night_auto_sync_enabled": False})
    assert config.night_auto_sync_enabled is False


def test_night_auto_sync_enabled_rejects_non_bool() -> None:
    with pytest.raises(InvalidRutScheduleConfig) as error:
        parse_rut_schedule_config({**_BASE, "night_auto_sync_enabled": "yes"})
    assert error.value.path == "config.night_auto_sync_enabled"


def test_other_keys_are_still_required() -> None:
    incomplete = dict(_BASE)
    del incomplete["title"]
    with pytest.raises(InvalidRutScheduleConfig, match="Missing fields"):
        parse_rut_schedule_config(incomplete)


def test_unknown_key_is_still_rejected() -> None:
    with pytest.raises(InvalidRutScheduleConfig, match="Unknown fields"):
        parse_rut_schedule_config({**_BASE, "unexpected": 1})
