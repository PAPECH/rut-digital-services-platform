from __future__ import annotations

import re
from typing import Any

from .errors import TestAnswerValidationError, TestSchemaValidationError

STRUCTURAL_TYPES = {"questionnaire_title", "section_title", "instruction"}
CHOICE_TYPES = {"single_choice", "multiple_choice", "scale"}
ANSWERABLE_TYPES = {"text"} | CHOICE_TYPES
ELEMENT_TYPES = STRUCTURAL_TYPES | ANSWERABLE_TYPES

MAX_ELEMENTS = 1000
MAX_OPTIONS = 20
MAX_LABEL_LENGTH = 2000
MAX_OPTION_LABEL_LENGTH = 500
MAX_TEXT_ANSWER_LENGTH = 2000

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _error(message: str, path: str) -> TestSchemaValidationError:
    return TestSchemaValidationError(message, path=path)


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


def _score(value: Any, *, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _error("Option score must be a number", path)
    return float(value)


def _validate_options(raw_options: Any, *, path: str) -> list[dict[str, Any]]:
    if not isinstance(raw_options, list) or not 1 <= len(raw_options) <= MAX_OPTIONS:
        raise _error(f"Options must contain between 1 and {MAX_OPTIONS} items", f"{path}.options")
    values: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, option in enumerate(raw_options):
        option_path = f"{path}.options[{index}]"
        if not isinstance(option, dict) or set(option) != {"value", "label", "score"}:
            raise _error("Option must contain exactly value, label, and score", option_path)
        value = _text(option.get("value"), path=f"{option_path}.value", required=True, max_length=100)
        label = _text(
            option.get("label"),
            path=f"{option_path}.label",
            required=True,
            max_length=MAX_OPTION_LABEL_LENGTH,
        )
        score = _score(option.get("score"), path=f"{option_path}.score")
        assert value is not None and label is not None
        if value in values:
            raise _error("Option values must be unique", f"{option_path}.value")
        values.add(value)
        normalized.append({"value": value, "label": label, "score": score})
    return normalized


def validate_elements(elements: Any) -> list[dict[str, Any]]:  # noqa: PLR0912
    """Normalize and validate the flat, ordered element sequence of a test schema.

    Flat rather than nested under sections, matching how RUT's own source content is
    actually shaped (see "RUT content import format" in the task doc) -- a
    `section_title` element is itself the section boundary in the sequence.
    """
    if not isinstance(elements, list):
        raise _error("elements must be a list", "elements")
    if len(elements) > MAX_ELEMENTS:
        raise _error(f"A test cannot contain more than {MAX_ELEMENTS} elements", "elements")

    normalized_elements: list[dict[str, Any]] = []
    keys: set[str] = set()
    scoring_keys: set[str] = set()
    for index, raw in enumerate(elements):
        path = f"elements[{index}]"
        if not isinstance(raw, dict):
            raise _error("Element must be an object", path)
        element_type = raw.get("type")
        if element_type not in ELEMENT_TYPES:
            raise _error("Unknown element type", f"{path}.type")

        key = _text(raw.get("key"), path=f"{path}.key", required=True, max_length=64)
        assert key is not None
        if not _KEY_RE.fullmatch(key):
            raise _error("Invalid element key", f"{path}.key")
        if key in keys:
            raise _error("Element keys must be unique", f"{path}.key")
        keys.add(key)

        label = _text(raw.get("label"), path=f"{path}.label", required=True, max_length=MAX_LABEL_LENGTH)
        assert label is not None

        if element_type in STRUCTURAL_TYPES:
            unknown = set(raw) - {"key", "type", "label"}
            if unknown:
                raise _error(f"Unknown element properties: {', '.join(sorted(unknown))}", path)
            normalized_elements.append({"key": key, "type": element_type, "label": label})
            continue

        allowed = {"key", "type", "label", "required"}
        if element_type in CHOICE_TYPES:
            allowed |= {"scoring_key", "options"}
        unknown = set(raw) - allowed
        if unknown:
            raise _error(f"Unknown element properties: {', '.join(sorted(unknown))}", path)

        required = _boolean(raw.get("required"), path=f"{path}.required", default=False)
        normalized: dict[str, Any] = {
            "key": key,
            "type": element_type,
            "label": label,
            "required": required,
        }

        if element_type in CHOICE_TYPES:
            # `scoring_key`/`options` are only ever set here, for a CHOICE_TYPES element -- never
            # added (not even as `None`) to a `text` element's normalized output, or this
            # function's own "unknown properties" check two lines below would reject its own
            # prior output on a second pass (a `text` element carrying a stray `scoring_key`
            # isn't in `allowed` for non-choice types): the exact idempotency trap already fixed
            # in `scoring.py`'s term-shape check, here for elements instead of result-scale terms.
            scoring_key = _text(
                raw.get("scoring_key"), path=f"{path}.scoring_key", required=False, max_length=64
            )
            if scoring_key is not None:
                if not _KEY_RE.fullmatch(scoring_key):
                    raise _error("Invalid scoring key", f"{path}.scoring_key")
                if scoring_key in scoring_keys:
                    raise _error("Scoring keys must be unique", f"{path}.scoring_key")
                scoring_keys.add(scoring_key)
            normalized["scoring_key"] = scoring_key
            normalized["options"] = _validate_options(raw.get("options"), path=path)

        normalized_elements.append(normalized)

    return normalized_elements


def known_scoring_keys(elements: list[dict[str, Any]]) -> set[str]:
    return {element["scoring_key"] for element in elements if element.get("scoring_key")}


def _validate_answer_value(element: dict[str, Any], raw: Any) -> Any:
    key = element["key"]
    element_type = element["type"]
    if element_type == "text":
        if not isinstance(raw, str):
            raise TestAnswerValidationError("Value must be a string", question_key=key)
        if len(raw) > MAX_TEXT_ANSWER_LENGTH:
            raise TestAnswerValidationError("Value is too long", question_key=key)
        return raw
    if element_type in {"single_choice", "scale"}:
        if not isinstance(raw, str):
            raise TestAnswerValidationError("Value must be an option value", question_key=key)
        allowed = {option["value"] for option in element["options"]}
        if raw not in allowed:
            raise TestAnswerValidationError("Unknown option value", question_key=key)
        return raw
    if element_type == "multiple_choice":
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            raise TestAnswerValidationError("Value must be a list of option values", question_key=key)
        allowed = {option["value"] for option in element["options"]}
        if any(item not in allowed for item in raw):
            raise TestAnswerValidationError("Unknown option value", question_key=key)
        if len(set(raw)) != len(raw):
            raise TestAnswerValidationError("Option values must be unique", question_key=key)
        return raw
    raise TestAnswerValidationError("Element is not answerable", question_key=key)


def validate_partial_answers(
    elements: list[dict[str, Any]],
    answers: dict[str, Any],
) -> dict[str, Any]:
    """Type-check whatever answers are present; used by autosave, where being incomplete is
    expected and required-ness is not yet enforced."""
    if not isinstance(answers, dict):
        raise TestAnswerValidationError("Answers must be an object")
    answerable = {element["key"]: element for element in elements if element["type"] in ANSWERABLE_TYPES}
    unknown = set(answers) - set(answerable)
    if unknown:
        raise TestAnswerValidationError("Unknown question key", question_key=sorted(unknown)[0])
    return {key: _validate_answer_value(answerable[key], raw) for key, raw in answers.items()}


def validate_complete_answers(
    elements: list[dict[str, Any]],
    answers: dict[str, Any],
) -> dict[str, Any]:
    """Same as `validate_partial_answers`, plus enforces every required question is answered;
    used only when finalizing an attempt."""
    normalized = validate_partial_answers(elements, answers)
    answerable = {element["key"]: element for element in elements if element["type"] in ANSWERABLE_TYPES}
    for key, element in answerable.items():
        if element["required"] and key not in normalized:
            raise TestAnswerValidationError("Required question is missing an answer", question_key=key)
    return normalized
