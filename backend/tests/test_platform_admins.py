from __future__ import annotations

from dataclasses import replace

from app.modules.platform_admins.application.commands import EnsurePlatformAdminCommand
from app.modules.platform_admins.application.use_cases import EnsurePlatformAdmin
from app.modules.platform_admins.domain.entities import GlobalAdminIdentity


class InMemoryPlatformAdminRepository:
    def __init__(self, identities: list[GlobalAdminIdentity] | None = None) -> None:
        self.items = {item.max_user_id: item for item in identities or []}
        self.next_id = max((item.id or 0 for item in self.items.values()), default=0) + 1

    def find_by_max_user_id(self, max_user_id: str) -> GlobalAdminIdentity | None:
        return self.items.get(max_user_id.strip())

    def list_platform_admins(self) -> list[GlobalAdminIdentity]:
        return [item for item in self.items.values() if item.role == "platform_admin"]

    def add(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        stored = replace(identity, id=self.next_id)
        self.next_id += 1
        self.items[stored.max_user_id] = stored
        return stored

    def update(self, identity: GlobalAdminIdentity) -> GlobalAdminIdentity:
        self.items[identity.max_user_id] = identity
        return identity


def test_ensure_platform_admin_is_idempotent() -> None:
    repository = InMemoryPlatformAdminRepository()
    service = EnsurePlatformAdmin(repository)
    command = EnsurePlatformAdminCommand(
        max_user_id=" 123456 ",
        full_name="  Иванов   Иван Иванович ",
    )

    created = service.execute(command)
    repeated = service.execute(command)

    assert created.created is True
    assert created.identity.id == 1
    assert created.identity.max_user_id == "123456"
    assert created.identity.full_name == "Иванов Иван Иванович"
    assert repeated.created is False
    assert repeated.identity.id == created.identity.id
    assert len(repository.items) == 1


def test_ensure_promotes_and_reactivates_existing_staff_identity() -> None:
    repository = InMemoryPlatformAdminRepository(
        [
            GlobalAdminIdentity(
                id=7,
                max_user_id="777",
                full_name="Старое имя",
                role="employee",
                is_active=False,
            )
        ]
    )

    result = EnsurePlatformAdmin(repository).execute(
        EnsurePlatformAdminCommand(max_user_id="777", full_name="Новое имя")
    )

    assert result.created is False
    assert result.previous_role == "employee"
    assert result.reactivated is True
    assert result.identity.id == 7
    assert result.identity.role == "platform_admin"
    assert result.identity.is_active is True
    assert result.identity.full_name == "Новое имя"
