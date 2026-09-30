from __future__ import annotations

import math
import re
from copy import deepcopy
from datetime import date
from typing import Any

FIELD_TYPES = {
    "short_text",
    "long_text",
    "email",
    "phone",
    "number",
    "date",
    "checkbox",
    "select",
    "radio",
    "multiselect",
    "file",
}

MAX_FIELDS = 100
MAX_OPTIONS = 100
MAX_LABEL_LENGTH = 300
MAX_HELP_LENGTH = 2_000
MAX_VALUE_LENGTH = 20_000
MAX_PATTERN_LENGTH = 500
MAX_FILES = 10
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_PROFILE_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_MIME_RE = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+*-]+$")
_HTML_TAG_RE = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")

_COMMON_KEYS = {
    "key",
    "type",
    "label",
    "help_text",
    "required",
    "active",
    "profile_key",
}
_TYPE_KEYS = {
    "short_text": {"placeholder", "default", "min_length", "max_length", "pattern"},
    "long_text": {"placeholder", "default", "min_length", "max_length"},
    "email": {"placeholder", "default"},
    "phone": {"placeholder", "default", "pattern"},
    "number": {"placeholder", "default", "min", "max", "step"},
    "date": {"default", "min", "max"},
    "checkbox": {"default"},
    "select": {"options", "default"},
    "radio": {"options", "default"},
    "multiselect": {"options", "default", "min_selected", "max_selected"},
    "file": {"accepted_mime_types", "max_files", "max_size_bytes"},
}


class FormSchemaValidationError(ValueError):
    def __init__(self, message: str, *, path: str = "fields") -> None:
        super().__init__(message)
        self.path = path


class FormValueValidationError(ValueError):
    def __init__(self, message: str, *, field_key: str | None = None) -> None:
        super().__init__(message)
        self.field_key = field_key


def clone_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(fields)


def _error(message: str, path: str) -> FormSchemaValidationError:
    return FormSchemaValidationError(message, path=path)


def _text(value: Any, *, path: str, required: bool, max_length: int) -> str | None:
    if value is None:
        if required:
            raise _error("Value is required", path)
        return None
    if not isinstance(value, str):
        raise _error("Value must be a string", path)
    if required and not value.strip():
        raise _error("Value cannot be blank", path)
    if len(value) > max_length:
        raise _error(f"Value is longer than {max_length} characters", path)
    return value


def _boolean(value: Any, *, path: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise _error("Value must be a boolean", path)
    return value


def _integer(
    value: Any,
    *,
    path: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error("Value must be an integer", path)
    if value < minimum or value > maximum:
        raise _error(f"Value must be between {minimum} and {maximum}", path)
    return value


def _number(value: Any, *, path: str, allow_none: bool = True) -> float | int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _error("Value must be a number", path)
    if not math.isfinite(float(value)):
        raise _error("Value must be finite", path)
    return value


def _iso_date(value: Any, *, path: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise _error("Value must be an ISO date", path)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise _error("Value must be an ISO date", path) from exc


def _pattern(value: Any, *, path: str) -> str | None:
    pattern = _text(value, path=path, required=False, max_length=MAX_PATTERN_LENGTH)
    if not pattern:
        return None
    try:
        re.compile(pattern)
    except re.error as exc:
        raise _error(f"Invalid regular expression: {exc}", path) from exc
    return pattern


def _reject_markup(value: str | None, *, path: str) -> None:
    if value and _HTML_TAG_RE.search(value):
        raise _error("HTML markup is not allowed", path)


def _validate_text_constraints(raw: dict[str, Any], normalized: dict[str, Any], path: str) -> None:
    min_length = _integer(
        raw.get("min_length"),
        path=f"{path}.min_length",
        default=0,
        minimum=0,
        maximum=MAX_VALUE_LENGTH,
    )
    max_length = _integer(
        raw.get("max_length"),
        path=f"{path}.max_length",
        default=MAX_VALUE_LENGTH,
        minimum=1,
        maximum=MAX_VALUE_LENGTH,
    )
    if min_length > max_length:
        raise _error("min_length cannot be greater than max_length", path)
    normalized["placeholder"] = _text(
        raw.get("placeholder"), path=f"{path}.placeholder", required=False, max_length=500
    )
    normalized["default"] = _text(
        raw.get("default"), path=f"{path}.default", required=False, max_length=max_length
    )
    normalized["min_length"] = min_length
    normalized["max_length"] = max_length
    if normalized["default"] is not None and len(normalized["default"]) < min_length:
        raise _error("Default is shorter than min_length", f"{path}.default")


def _validate_options(raw: dict[str, Any], normalized: dict[str, Any], path: str) -> None:
    options = raw.get("options")
    if not isinstance(options, list) or not 1 <= len(options) <= MAX_OPTIONS:
        raise _error(f"Options must contain between 1 and {MAX_OPTIONS} items", f"{path}.options")
    values: set[str] = set()
    normalized_options: list[dict[str, str]] = []
    for option_index, option in enumerate(options):
        option_path = f"{path}.options[{option_index}]"
        if not isinstance(option, dict) or set(option) != {"value", "label"}:
            raise _error("Option must contain only value and label", option_path)
        value = _text(option.get("value"), path=f"{option_path}.value", required=True, max_length=100)
        label = _text(option.get("label"), path=f"{option_path}.label", required=True, max_length=300)
        assert value is not None and label is not None
        if value in values:
            raise _error("Option values must be unique", f"{option_path}.value")
        values.add(value)
        normalized_options.append({"value": value, "label": label})
    default = _text(raw.get("default"), path=f"{path}.default", required=False, max_length=100)
    if default is not None and default not in values:
        raise _error("Default must match an option value", f"{path}.default")
    normalized["options"] = normalized_options
    normalized["default"] = default


def _validate_multiselect_options(raw: dict[str, Any], normalized: dict[str, Any], path: str) -> None:
    options = raw.get("options")
    if not isinstance(options, list) or not 1 <= len(options) <= MAX_OPTIONS:
        raise _error(f"Options must contain between 1 and {MAX_OPTIONS} items", f"{path}.options")
    values: set[str] = set()
    normalized_options: list[dict[str, str]] = []
    for option_index, option in enumerate(options):
        option_path = f"{path}.options[{option_index}]"
        if not isinstance(option, dict) or set(option) != {"value", "label"}:
            raise _error("Option must contain only value and label", option_path)
        value = _text(option.get("value"), path=f"{option_path}.value", required=True, max_length=100)
        label = _text(option.get("label"), path=f"{option_path}.label", required=True, max_length=300)
        assert value is not None and label is not None
        if value in values:
            raise _error("Option values must be unique", f"{option_path}.value")
        values.add(value)
        normalized_options.append({"value": value, "label": label})

    default_raw = raw.get("default")
    normalized_default: list[str] | None = None
    if default_raw is not None:
        if not isinstance(default_raw, list):
            raise _error("Default must be a list of option values", f"{path}.default")
        seen: set[str] = set()
        normalized_default = []
        for default_index, item in enumerate(default_raw):
            item_path = f"{path}.default[{default_index}]"
            if not isinstance(item, str):
                raise _error("Default entries must be strings", item_path)
            if item not in values:
                raise _error("Default must match an option value", item_path)
            if item in seen:
                raise _error("Default entries must be unique", item_path)
            seen.add(item)
            normalized_default.append(item)

    min_selected = _integer(
        raw.get("min_selected"),
        path=f"{path}.min_selected",
        default=0,
        minimum=0,
        maximum=len(normalized_options),
    )
    max_selected = _integer(
        raw.get("max_selected"),
        path=f"{path}.max_selected",
        default=len(normalized_options),
        minimum=0,
        maximum=len(normalized_options),
    )
    if min_selected > max_selected:
        raise _error("min_selected cannot be greater than max_selected", path)

    normalized["options"] = normalized_options
    normalized["default"] = normalized_default
    normalized["min_selected"] = min_selected
    normalized["max_selected"] = max_selected


def validate_form_fields(  # noqa: PLR0912, PLR0915
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(fields, list):
        raise _error("Fields must be a list", "fields")
    if len(fields) > MAX_FIELDS:
        raise _error(f"A form cannot contain more than {MAX_FIELDS} fields", "fields")

    normalized_fields: list[dict[str, Any]] = []
    keys: set[str] = set()
    for index, raw in enumerate(fields):
        path = f"fields[{index}]"
        if not isinstance(raw, dict):
            raise _error("Field must be an object", path)
        field_type = raw.get("type")
        if field_type not in FIELD_TYPES:
            raise _error("Unknown field type", f"{path}.type")
        allowed = _COMMON_KEYS | _TYPE_KEYS[field_type]
        unknown = set(raw) - allowed
        if unknown:
            raise _error(f"Unknown field properties: {', '.join(sorted(unknown))}", path)

        key = _text(raw.get("key"), path=f"{path}.key", required=True, max_length=64)
        assert key is not None
        if not _KEY_RE.fullmatch(key):
            raise _error("Invalid field key", f"{path}.key")
        if key in keys:
            raise _error("Field keys must be unique", f"{path}.key")
        keys.add(key)

        profile_key = _text(
            raw.get("profile_key"),
            path=f"{path}.profile_key",
            required=False,
            max_length=80,
        )
        if profile_key is not None and not _PROFILE_KEY_RE.fullmatch(profile_key):
            raise _error("Invalid profile key", f"{path}.profile_key")

        label = _text(raw.get("label"), path=f"{path}.label", required=True, max_length=MAX_LABEL_LENGTH)
        assert label is not None
        _reject_markup(label, path=f"{path}.label")
        help_text = _text(
            raw.get("help_text"),
            path=f"{path}.help_text",
            required=False,
            max_length=MAX_HELP_LENGTH,
        )
        _reject_markup(help_text, path=f"{path}.help_text")
        normalized: dict[str, Any] = {
            "key": key,
            "type": field_type,
            "label": label,
            "help_text": help_text,
            "required": _boolean(raw.get("required"), path=f"{path}.required", default=False),
            "active": _boolean(raw.get("active"), path=f"{path}.active", default=True),
            "profile_key": profile_key,
        }

        if field_type in {"short_text", "long_text"}:
            _validate_text_constraints(raw, normalized, path)
            if field_type == "short_text":
                normalized["pattern"] = _pattern(raw.get("pattern"), path=f"{path}.pattern")
                if (
                    normalized["default"] is not None
                    and normalized["pattern"]
                    and re.fullmatch(normalized["pattern"], normalized["default"]) is None
                ):
                    raise _error("Default does not match the required format", f"{path}.default")
        elif field_type in {"email", "phone"}:
            normalized["placeholder"] = _text(
                raw.get("placeholder"),
                path=f"{path}.placeholder",
                required=False,
                max_length=500,
            )
            normalized["default"] = _text(
                raw.get("default"),
                path=f"{path}.default",
                required=False,
                max_length=320 if field_type == "email" else 100,
            )
            if (
                field_type == "email"
                and normalized["default"]
                and _EMAIL_RE.fullmatch(normalized["default"]) is None
            ):
                raise _error("Invalid default email address", f"{path}.default")
            if field_type == "phone":
                normalized["pattern"] = _pattern(raw.get("pattern"), path=f"{path}.pattern")
                if (
                    normalized["default"] is not None
                    and normalized["pattern"]
                    and re.fullmatch(normalized["pattern"], normalized["default"]) is None
                ):
                    raise _error("Default phone does not match the required format", f"{path}.default")
        elif field_type == "number":
            minimum = _number(raw.get("min"), path=f"{path}.min")
            maximum = _number(raw.get("max"), path=f"{path}.max")
            default = _number(raw.get("default"), path=f"{path}.default")
            step = _number(raw.get("step", 1), path=f"{path}.step", allow_none=False)
            assert step is not None
            if step <= 0:
                raise _error("Step must be positive", f"{path}.step")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise _error("Minimum cannot be greater than maximum", path)
            if default is not None and minimum is not None and default < minimum:
                raise _error("Default is smaller than minimum", f"{path}.default")
            if default is not None and maximum is not None and default > maximum:
                raise _error("Default is greater than maximum", f"{path}.default")
            normalized.update(
                {
                    "placeholder": _text(
                        raw.get("placeholder"),
                        path=f"{path}.placeholder",
                        required=False,
                        max_length=500,
                    ),
                    "default": default,
                    "min": minimum,
                    "max": maximum,
                    "step": step,
                }
            )
        elif field_type == "date":
            minimum = _iso_date(raw.get("min"), path=f"{path}.min")
            maximum = _iso_date(raw.get("max"), path=f"{path}.max")
            default = _iso_date(raw.get("default"), path=f"{path}.default")
            if minimum and maximum and minimum > maximum:
                raise _error("Minimum date cannot be after maximum date", path)
            if default and minimum and default < minimum:
                raise _error("Default date is before minimum", f"{path}.default")
            if default and maximum and default > maximum:
                raise _error("Default date is after maximum", f"{path}.default")
            normalized.update({"default": default, "min": minimum, "max": maximum})
        elif field_type == "checkbox":
            normalized["default"] = _boolean(raw.get("default"), path=f"{path}.default", default=False)
        elif field_type in {"select", "radio"}:
            _validate_options(raw, normalized, path)
        elif field_type == "multiselect":
            _validate_multiselect_options(raw, normalized, path)
        elif field_type == "file":
            accepted = raw.get("accepted_mime_types", [])
            if not isinstance(accepted, list) or len(accepted) > 30:
                raise _error("accepted_mime_types must be a list", f"{path}.accepted_mime_types")
            normalized_mime: list[str] = []
            for mime_index, mime in enumerate(accepted):
                if not isinstance(mime, str) or not _MIME_RE.fullmatch(mime):
                    raise _error(
                        "Invalid MIME type",
                        f"{path}.accepted_mime_types[{mime_index}]",
                    )
                if mime not in normalized_mime:
                    normalized_mime.append(mime)
            normalized.update(
                {
                    "accepted_mime_types": normalized_mime,
                    "max_files": _integer(
                        raw.get("max_files"),
                        path=f"{path}.max_files",
                        default=1,
                        minimum=1,
                        maximum=MAX_FILES,
                    ),
                    "max_size_bytes": _integer(
                        raw.get("max_size_bytes"),
                        path=f"{path}.max_size_bytes",
                        default=MAX_FILE_SIZE_BYTES,
                        minimum=1,
                        maximum=MAX_FILE_SIZE_BYTES,
                    ),
                }
            )
        normalized_fields.append(normalized)
    return normalized_fields


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def _value_error(message: str, key: str) -> FormValueValidationError:
    return FormValueValidationError(message, field_key=key)


def _validate_string_value(field: dict[str, Any], raw: Any) -> str:
    key = field["key"]
    if not isinstance(raw, str):
        raise _value_error("Value must be a string", key)
    field_type = field["type"]
    if field_type in {"short_text", "long_text"}:
        if len(raw) < field["min_length"] or len(raw) > field["max_length"]:
            raise _value_error("Text length is outside the allowed range", key)
        pattern = field.get("pattern")
        if pattern and re.fullmatch(pattern, raw) is None:
            raise _value_error("Value does not match the required format", key)
    elif field_type == "email":
        if len(raw) > 320 or _EMAIL_RE.fullmatch(raw) is None:
            raise _value_error("Invalid email address", key)
    elif field_type == "phone":
        if len(raw) > 100:
            raise _value_error("Phone number is too long", key)
        pattern = field.get("pattern")
        if pattern and re.fullmatch(pattern, raw) is None:
            raise _value_error("Phone number does not match the required format", key)
    return raw


def _validate_value(field: dict[str, Any], raw: Any) -> Any:  # noqa: PLR0912
    key = field["key"]
    field_type = field["type"]
    if field_type in {"short_text", "long_text", "email", "phone"}:
        return _validate_string_value(field, raw)
    if field_type == "number":
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            raise _value_error("Value must be a number", key)
        number = float(raw)
        if not math.isfinite(number):
            raise _value_error("Value must be finite", key)
        if field["min"] is not None and number < float(field["min"]):
            raise _value_error("Value is smaller than minimum", key)
        if field["max"] is not None and number > float(field["max"]):
            raise _value_error("Value is greater than maximum", key)
        step = float(field["step"])
        base = float(field["min"] or 0)
        quotient = (number - base) / step
        if not math.isclose(quotient, round(quotient), abs_tol=1e-9):
            raise _value_error("Value does not match the configured step", key)
        return raw
    if field_type == "date":
        if not isinstance(raw, str):
            raise _value_error("Value must be an ISO date", key)
        try:
            value = date.fromisoformat(raw).isoformat()
        except ValueError as exc:
            raise _value_error("Value must be an ISO date", key) from exc
        if field["min"] and value < field["min"]:
            raise _value_error("Date is before minimum", key)
        if field["max"] and value > field["max"]:
            raise _value_error("Date is after maximum", key)
        return value
    if field_type == "checkbox":
        if not isinstance(raw, bool):
            raise _value_error("Value must be a boolean", key)
        if field["required"] and not raw:
            raise _value_error("Checkbox must be selected", key)
        return raw
    if field_type in {"select", "radio"}:
        if not isinstance(raw, str):
            raise _value_error("Value must be an option value", key)
        allowed = {option["value"] for option in field["options"]}
        if raw not in allowed:
            raise _value_error("Unknown option value", key)
        return raw
    if field_type == "multiselect":
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            raise _value_error("Value must be a list of option values", key)
        allowed = {option["value"] for option in field["options"]}
        if any(item not in allowed for item in raw):
            raise _value_error("Unknown option value", key)
        if len(set(raw)) != len(raw):
            raise _value_error("Option values must be unique", key)
        min_selected = field["min_selected"]
        if field["required"] and min_selected == 0:
            min_selected = 1
        if len(raw) < min_selected or len(raw) > field["max_selected"]:
            raise _value_error("Number of selected options is outside the allowed range", key)
        return raw
    if field_type == "file":
        values = raw if isinstance(raw, list) else [raw]
        if not values or len(values) > field["max_files"]:
            raise _value_error("Invalid number of files", key)
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
            raise _value_error("File value must contain attachment IDs", key)
        if len(set(values)) != len(values):
            raise _value_error("Attachment IDs must be unique", key)
        return values
    raise _value_error("Unknown field type", key)


def validate_submission_values(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
) -> dict[str, Any]:
    normalized_fields = validate_form_fields(fields)
    if not isinstance(values, dict):
        raise FormValueValidationError("Values must be an object")
    active_fields = {field["key"]: field for field in normalized_fields if field["active"]}
    unknown = set(values) - set(active_fields)
    if unknown:
        key = sorted(unknown)[0]
        raise _value_error("Unknown or inactive form field", key)

    normalized_values: dict[str, Any] = {}
    for key, field in active_fields.items():
        present = key in values and not _is_empty(values[key])
        if not present:
            default = field.get("default")
            if field["type"] == "checkbox" and key in values:
                present = True
                default = values[key]
            if default is not None and not (field["type"] == "file"):
                normalized_values[key] = _validate_value(field, default)
                continue
            if field["required"]:
                raise _value_error("Required field is missing", key)
            continue
        normalized_values[key] = _validate_value(field, values[key])
    return normalized_values


def extract_attachment_ids(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
) -> dict[int, tuple[str, dict[str, Any]]]:
    by_key = {field["key"]: field for field in validate_form_fields(fields)}
    result: dict[int, tuple[str, dict[str, Any]]] = {}
    for key, raw in values.items():
        field = by_key.get(key)
        if field is None or field["type"] != "file":
            continue
        for attachment_id in raw:
            result[attachment_id] = (key, field)
    return result
