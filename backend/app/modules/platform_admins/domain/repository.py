from __future__ import annotations

from typing import Protocol

from .entities import GlobalAdminIdentity


class PlatformAdminRepository(Protocol):
    def find_by_max_user_id(self, max_user_id: str) -> GlobalAdminIdentity | None: ...

    def list_platform_admins(self) -> list[GlobalAdminIdentity]: ...

    def add(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity: ...

    def update(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity: ...
