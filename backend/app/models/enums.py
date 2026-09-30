from enum import StrEnum

from ..modules.admins.domain.admin_account import AdminRoleEnum  # noqa: F401 -- re-exported


class SystemEnum(StrEnum):
    max = "max"
    beavers = "beavers"


class FieldTypeEnum(StrEnum):
    string = "string"
    number = "number"
    date = "date"
    checkbox = "checkbox"


class SubmissionStatusEnum(StrEnum):
    new = "new"
    in_work = "in_work"
    rejected = "rejected"
    done = "done"


class MessageDirectionEnum(StrEnum):
    in_ = "in"
    out = "out"


class TicketStatusEnum(StrEnum):
    open = "open"
    answered = "answered"
