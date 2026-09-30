from datetime import date

from app.modules.profiles.domain.entities import SharedProfile
from app.modules.profiles.domain.requirements import find_missing_required_fields

SCHEMA = [
    {"key": "job_title", "label": "Должность", "type": "string", "required": True},
    {
        "key": "structural_unit",
        "label": "Подразделение",
        "type": "string",
        "required": True,
    },
]


def test_required_profile_fields_include_verified_phone_and_organization_data() -> None:
    profile = SharedProfile(
        user_id=1,
        external_user_id="max-1",
        provider="max",
        first_name="Иван",
        last_name="Иванов",
        patronymic="Иванович",
        phone="+70000000000",
        phone_verified=False,
        email="ivan@example.test",
        birth_date=date(2000, 1, 1),
        job_title=None,
        structural_unit="  ",
    )

    assert find_missing_required_fields(profile, SCHEMA) == [
        "Подтверждённый телефон",
        "Должность",
        "Подразделение",
    ]


def test_custom_shared_profile_field_is_supported() -> None:
    profile = SharedProfile(
        user_id=1,
        external_user_id="max-1",
        provider="max",
        first_name="Иван",
        last_name="Иванов",
        patronymic="Иванович",
        phone="+70000000000",
        phone_verified=True,
        email="ivan@example.test",
        birth_date=date(2000, 1, 1),
        shared_data={"custom_code": "RUT-17"},
    )
    assert (
        find_missing_required_fields(
            profile,
            [{"key": "custom_code", "label": "Код", "type": "string", "required": True}],
        )
        == []
    )


def test_custom_bot_local_profile_field_is_scoped_to_membership() -> None:
    profile = SharedProfile(
        user_id=1,
        external_user_id="max-1",
        provider="max",
        first_name="Иван",
        last_name="Иванов",
        patronymic="Иванович",
        phone="+70000000000",
        phone_verified=True,
        email="ivan@example.test",
        birth_date=date(2000, 1, 1),
    )
    schema = [{"key": "department_code", "label": "Код", "required": True}]

    assert find_missing_required_fields(profile, schema, {"department_code": "A-1"}) == []
    assert find_missing_required_fields(profile, schema, {}) == ["Код"]
