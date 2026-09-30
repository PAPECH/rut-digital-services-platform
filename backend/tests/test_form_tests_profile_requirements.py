"""Task 080: `form_tests`' own extra profile-completeness requirement (birth date, email) layered
on top of the platform's shared check -- deliberately does not touch
`profiles.domain.requirements.CORE_REQUIREMENTS`, which `modules/forms` also relies on."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from app.modules.form_tests.application.profile_requirements import (
    find_missing_test_participation_fields,
)
from app.modules.profiles.domain.entities import SharedProfile

_COMPLETE = SharedProfile(
    user_id=1,
    external_user_id="ext-1",
    provider="max",
    last_name="Иванов",
    first_name="Иван",
    patronymic="Иванович",
    phone="+79990000000",
    phone_verified=True,
    birth_date=date(2000, 1, 2),
    email="ivan@example.com",
)


def test_complete_profile_has_no_missing_fields() -> None:
    assert find_missing_test_participation_fields(_COMPLETE) == []


def test_missing_birth_date_is_reported() -> None:
    missing = find_missing_test_participation_fields(replace(_COMPLETE, birth_date=None))
    assert missing == ["Дата рождения"]


def test_missing_email_is_reported() -> None:
    missing = find_missing_test_participation_fields(replace(_COMPLETE, email=None))
    assert missing == ["Email"]


def test_blank_email_is_treated_as_missing() -> None:
    missing = find_missing_test_participation_fields(replace(_COMPLETE, email="   "))
    assert missing == ["Email"]


def test_missing_core_fields_and_extra_fields_combine() -> None:
    profile = replace(_COMPLETE, last_name=None, birth_date=None, email=None)
    missing = find_missing_test_participation_fields(profile)
    assert missing == ["Фамилия", "Дата рождения", "Email"]
