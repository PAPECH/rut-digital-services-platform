from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.modules.admin_invites.application.ports import GrantOutcome, InviteeInactive
from app.modules.admin_invites.domain.entities import AdminInvite, InviteKind
from app.modules.bot_instances.domain.staff_access import StaffPermissions

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


class InMemoryInviteRepository:
    def __init__(self) -> None:
        self.items: dict[int, AdminInvite] = {}
        self.hashes: dict[str, int] = {}
        self.next_id = 1

    def add(self, invite: AdminInvite, token_hash: str) -> AdminInvite:
        stored = replace(invite, id=self.next_id, created_at=NOW)
        self.items[self.next_id] = stored
        self.hashes[token_hash] = self.next_id
        self.next_id += 1
        return stored

    def list(self, kind: InviteKind, bot_instance_id: int | None) -> list[AdminInvite]:
        return [
            item
            for item in self.items.values()
            if item.kind == kind and item.bot_instance_id == bot_instance_id
        ]

    def get(self, invite_id: int, kind: InviteKind, bot_instance_id: int | None) -> AdminInvite | None:
        item = self.items.get(invite_id)
        if item is None or item.kind != kind or item.bot_instance_id != bot_instance_id:
            return None
        return item

    def get_by_token_hash_for_update(self, token_hash: str) -> AdminInvite | None:
        invite_id = self.hashes.get(token_hash)
        return self.items.get(invite_id) if invite_id is not None else None

    def increment_used(self, invite_id: int) -> AdminInvite:
        item = self.items[invite_id]
        self.items[invite_id] = replace(item, used_count=item.used_count + 1)
        return self.items[invite_id]

    def revoke(self, invite_id: int, revoked_at: datetime) -> AdminInvite:
        self.items[invite_id] = replace(self.items[invite_id], revoked_at=revoked_at)
        return self.items[invite_id]


class SequentialInviteCodec:
    def __init__(self) -> None:
        self.counter = 0

    def generate(self) -> str:
        self.counter += 1
        return f"invite-token-{self.counter:04d}-abcdef"

    def digest(self, raw_token: str) -> str:
        return f"digest:{raw_token}"


class RecordingGrants:
    def __init__(self, *, inactive: set[str] | None = None) -> None:
        self.platform: list[tuple[str, str]] = []
        self.bot_staff: list[tuple[int, str, str, str, StaffPermissions]] = []
        self.admin_ids: dict[str, int] = {}
        self.inactive = inactive or set()

    def _admin_id(self, max_user_id: str) -> GrantOutcome:
        created = max_user_id not in self.admin_ids
        self.admin_ids.setdefault(max_user_id, 100 + len(self.admin_ids))
        return GrantOutcome(admin_id=self.admin_ids[max_user_id], created=created)

    def grant_platform_admin(self, max_user_id: str, full_name: str) -> GrantOutcome:
        self.platform.append((max_user_id, full_name))
        return self._admin_id(max_user_id)

    def grant_bot_staff(
        self,
        bot_instance_id: int,
        max_user_id: str,
        full_name: str,
        role: str,
        permissions: StaffPermissions,
    ) -> GrantOutcome:
        if max_user_id in self.inactive:
            raise InviteeInactive(max_user_id)
        self.bot_staff.append((bot_instance_id, max_user_id, full_name, role, permissions))
        return self._admin_id(max_user_id)
