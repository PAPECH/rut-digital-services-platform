from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GlobalAdminRole = Literal["employee", "admin", "platform_admin"]


@dataclass(frozen=True, slots=True)
class GlobalAdminIdentity:
    id: int | None
    max_user_id: str
    full_name: str
    role: GlobalAdminRole
    is_active: bool = True

    def __post_init__(self) -> None:
        max_user_id = self.max_user_id.strip()
        full_name = " ".join(self.full_name.split())
        if not max_user_id:
            raise ValueError("MAX user ID is required")
        if not full_name:
            raise ValueError("Full name is required")
        if len(max_user_id) > 64:
            raise ValueError("MAX user ID is too long")
        if len(full_name) > 200:
            raise ValueError("Full name is too long")
        object.__setattr__(self, "max_user_id", max_user_id)
        object.__setattr__(self, "full_name", full_name)
