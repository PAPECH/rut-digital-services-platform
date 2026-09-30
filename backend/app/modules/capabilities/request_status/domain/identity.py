import hashlib
import re

_SPACE_RE = re.compile(r"\s+")


class InvalidRequestNumber(ValueError):
    pass


def normalize_request_number(value: str, mode: str) -> str:
    if not isinstance(value, str):
        raise InvalidRequestNumber("Request number must be text")
    normalized = value.strip()
    if mode == "compact":
        normalized = _SPACE_RE.sub("", normalized).upper()
    elif mode != "trim":
        raise InvalidRequestNumber("Unsupported request-number normalization")
    if not normalized or len(normalized) > 64:
        raise InvalidRequestNumber("Request number must contain 1-64 characters")
    if any(ord(character) < 32 for character in normalized):
        raise InvalidRequestNumber("Request number contains control characters")
    return normalized


def request_number_hash(bot_instance_id: int, normalized_number: str) -> str:
    payload = f"{bot_instance_id}:{normalized_number}".encode()
    return hashlib.sha256(payload).hexdigest()
