"""Серверная валидация значений заявки по правилам полей формы (§6, §8.4 ТЗ).

Дублирует клиентскую валидацию: regexp, min/max, required, тип. Клиенту
доверять нельзя, поэтому всегда повторяем здесь.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from ..core.errors import bad_request
from ..models.enums import FieldTypeEnum
from ..models.form import FormField


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _validate_one(field: FormField, raw: Any) -> Any:
    label = field.label or f"#{field.id}"
    empty = raw is None or (isinstance(raw, str) and raw.strip() == "")

    if empty:
        if field.is_required:
            raise bad_request(f"Поле «{label}» обязательно", code="field_required", field_id=field.id)
        return None

    if field.type == FieldTypeEnum.string:
        value = _to_str(raw)
        if field.regexp:
            try:
                if not re.fullmatch(field.regexp, value):
                    raise bad_request(
                        f"Поле «{label}» не соответствует формату",
                        code="field_regexp",
                        field_id=field.id,
                    )
            except re.error as e:
                raise bad_request(
                    f"Невалидный regexp в поле «{label}»: {e}",
                    code="field_bad_regexp",
                    field_id=field.id,
                ) from e
        return value

    if field.type == FieldTypeEnum.number:
        try:
            num = float(raw)
        except (TypeError, ValueError) as e:
            raise bad_request(
                f"Поле «{label}» должно быть числом", code="field_number", field_id=field.id
            ) from e
        if field.min_value not in (None, ""):
            if num < float(field.min_value):
                raise bad_request(
                    f"Поле «{label}» меньше минимально допустимого {field.min_value}",
                    code="field_min",
                    field_id=field.id,
                )
        if field.max_value not in (None, ""):
            if num > float(field.max_value):
                raise bad_request(
                    f"Поле «{label}» больше максимально допустимого {field.max_value}",
                    code="field_max",
                    field_id=field.id,
                )
        return num

    if field.type == FieldTypeEnum.date:
        try:
            d = date.fromisoformat(_to_str(raw))
        except ValueError as e:
            raise bad_request(
                f"Поле «{label}» должно быть датой YYYY-MM-DD",
                code="field_date",
                field_id=field.id,
            ) from e
        if field.min_value:
            try:
                if d < date.fromisoformat(field.min_value):
                    raise bad_request(
                        f"Поле «{label}» раньше допустимого {field.min_value}",
                        code="field_min_date",
                        field_id=field.id,
                    )
            except ValueError:
                pass
        if field.max_value:
            try:
                if d > date.fromisoformat(field.max_value):
                    raise bad_request(
                        f"Поле «{label}» позже допустимого {field.max_value}",
                        code="field_max_date",
                        field_id=field.id,
                    )
            except ValueError:
                pass
        return d.isoformat()

    if field.type == FieldTypeEnum.checkbox:
        if isinstance(raw, bool):
            return raw
        s = _to_str(raw).strip().lower()
        if s in ("true", "1", "yes", "on", "да"):
            return True
        if s in ("false", "0", "no", "off", "нет", ""):
            return False
        raise bad_request(f"Поле «{label}» должно быть да/нет", code="field_checkbox", field_id=field.id)

    raise bad_request(f"Неизвестный тип поля {field.type}", code="field_type", field_id=field.id)


def validate_values(fields: list[FormField], values: dict[str, Any]) -> dict[str, Any]:
    """Прогнать все значения через правила. Возвращает нормализованный dict (ключ — str(field_id))."""
    out: dict[str, Any] = {}
    by_id = {str(f.id): f for f in fields if f.is_active}
    inactive_ids = {str(f.id) for f in fields if not f.is_active}

    # Игнорируем неактивные поля — на клиенте они не должны были присылаться
    for k, v in values.items():
        if k in inactive_ids:
            continue
        field = by_id.get(k)
        if field is None:
            # Незнакомое поле — игнорируем (защита от мусора с клиента)
            continue
        out[k] = _validate_one(field, v)

    # Заполняем дефолтами поля, которые клиент не прислал
    for fid, field in by_id.items():
        if fid in out:
            continue
        if field.default_value is not None:
            out[fid] = _validate_one(field, field.default_value)
        elif field.is_required:
            raise bad_request(f"Поле «{field.label}» обязательно", code="field_required", field_id=field.id)
    return out
