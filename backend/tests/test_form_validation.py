"""Тесты серверной валидации значений заявки (§6, §8.4 ТЗ)."""

from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.models.enums import FieldTypeEnum
from app.services.form_validation import validate_values


def _field(
    fid: int,
    *,
    label: str = "Поле",
    type: FieldTypeEnum = FieldTypeEnum.string,
    is_required: bool = False,
    is_active: bool = True,
    regexp: str | None = None,
    min_value: str | None = None,
    max_value: str | None = None,
    default_value: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=fid,
        label=label,
        type=type,
        is_required=is_required,
        is_active=is_active,
        regexp=regexp,
        min_value=min_value,
        max_value=max_value,
        default_value=default_value,
    )


def test_required_missing_raises():
    fields = [_field(1, is_required=True)]
    with pytest.raises(ApiError) as ei:
        validate_values(fields, {})
    assert ei.value.detail["code"] == "field_required"


def test_string_regexp_ok():
    fields = [_field(1, type=FieldTypeEnum.string, regexp=r"\d{3}")]
    out = validate_values(fields, {"1": "123"})
    assert out == {"1": "123"}


def test_string_regexp_fail():
    fields = [_field(1, type=FieldTypeEnum.string, regexp=r"\d{3}")]
    with pytest.raises(ApiError) as ei:
        validate_values(fields, {"1": "ab"})
    assert ei.value.detail["code"] == "field_regexp"


def test_number_range_ok():
    fields = [_field(1, type=FieldTypeEnum.number, min_value="1", max_value="10")]
    assert validate_values(fields, {"1": 5}) == {"1": 5.0}


def test_number_below_min():
    fields = [_field(1, type=FieldTypeEnum.number, min_value="5")]
    with pytest.raises(ApiError) as ei:
        validate_values(fields, {"1": 4})
    assert ei.value.detail["code"] == "field_min"


def test_date_format():
    fields = [_field(1, type=FieldTypeEnum.date)]
    assert validate_values(fields, {"1": "2024-05-01"}) == {"1": "2024-05-01"}


def test_date_bad_format():
    fields = [_field(1, type=FieldTypeEnum.date)]
    with pytest.raises(ApiError) as ei:
        validate_values(fields, {"1": "01.05.2024"})
    assert ei.value.detail["code"] == "field_date"


def test_checkbox_truthy_strings():
    fields = [_field(1, type=FieldTypeEnum.checkbox)]
    assert validate_values(fields, {"1": "true"}) == {"1": True}
    assert validate_values(fields, {"1": "Нет"}) == {"1": False}


def test_default_applies_when_missing():
    fields = [_field(1, default_value="abc")]
    assert validate_values(fields, {}) == {"1": "abc"}


def test_inactive_field_skipped():
    """Неактивное поле игнорируется — даже если клиент его прислал."""
    fields = [_field(1, is_active=False, is_required=True)]
    # Клиент прислал неактивное поле — игнорируем
    assert validate_values(fields, {"1": "x"}) == {}


def test_unknown_field_ignored():
    """Поля, которых нет в шаблоне, игнорируются (защита от мусора)."""
    fields = [_field(1)]
    assert validate_values(fields, {"99": "evil"}) == {}
