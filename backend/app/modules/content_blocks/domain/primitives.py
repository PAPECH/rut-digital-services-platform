from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from .errors import BlockValidationError

BLOCK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel"}


def strict_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    path: str,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise BlockValidationError(f"Missing fields: {', '.join(sorted(missing))}", path=path)
    if unknown:
        raise BlockValidationError(f"Unknown fields: {', '.join(sorted(unknown))}", path=path)


def text(value: Any, *, path: str, maximum: int, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise BlockValidationError("Expected text", path=path)
    normalized = value.strip()
    if required and not normalized:
        raise BlockValidationError("Text cannot be empty", path=path)
    if len(normalized) > maximum:
        raise BlockValidationError(f"Text exceeds {maximum} characters", path=path)
    return normalized or None


def stable_id(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or not BLOCK_ID_RE.fullmatch(value):
        raise BlockValidationError("Invalid stable id", path=path)
    return value


def url(value: Any, *, path: str, required: bool = True) -> str | None:
    normalized = text(value, path=path, maximum=2000, required=required)
    if normalized is None:
        return None
    parsed = urlsplit(normalized)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise BlockValidationError("Unsupported URL scheme", path=path)
    if parsed.scheme.lower() in {"http", "https"} and not parsed.netloc:
        raise BlockValidationError("URL host is required", path=path)
    return normalized


def items(value: Any, *, path: str, maximum: int = 50) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise BlockValidationError("Expected a non-empty item list", path=path)
    if len(value) > maximum:
        raise BlockValidationError(f"Too many items; maximum is {maximum}", path=path)
    if not all(isinstance(item, Mapping) for item in value):
        raise BlockValidationError("Every item must be an object", path=path)
    return value


def list_of_lists(value: Any, *, path: str, maximum: int = 50) -> list[list[Any]]:
    if not isinstance(value, list) or not value:
        raise BlockValidationError("Expected a non-empty item list", path=path)
    if len(value) > maximum:
        raise BlockValidationError(f"Too many items; maximum is {maximum}", path=path)
    if not all(isinstance(item, list) for item in value):
        raise BlockValidationError("Every item must be a list", path=path)
    return value
