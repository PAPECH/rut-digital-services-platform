import hashlib
import re

_CODE_RE = re.compile(r"^[A-Za-zА-Яа-я0-9._/-]{1,64}$")


class InvalidApplicantCode(ValueError):
    pass


def normalize_applicant_code(value: str) -> str:
    normalized = "".join(value.strip().split()).upper()
    if not _CODE_RE.fullmatch(normalized):
        raise InvalidApplicantCode("Applicant code has an invalid format")
    return normalized


def applicant_code_hash(bot_instance_id: int, normalized: str) -> str:
    return hashlib.sha256(f"{bot_instance_id}:{normalized}".encode()).hexdigest()
