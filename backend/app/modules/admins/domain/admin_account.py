from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

AdminRole = Literal["employee", "admin", "platform_admin"]


class AdminRoleEnum(StrEnum):
    """SQLAlchemy/Pydantic-facing counterpart of `AdminRole`.

    Lives here (not `backend/app/models/enums.py`, which re-exports it for backward
    compatibility) so `modules/admins/infrastructure/models.py` never needs to import from the
    `app.models` package — that package's own `__init__.py` re-exports `Admin` *from* this
    module, and a dependency back the other way (this module needing something from
    `app.models`) would be a circular import.
    """

    employee = "employee"
    admin = "admin"
    platform_admin = "platform_admin"


@dataclass(frozen=True, slots=True)
class AdminAccount:
    id: int | None
    max_user_id: str
    full_name: str
    role: AdminRole
    is_active: bool = True
