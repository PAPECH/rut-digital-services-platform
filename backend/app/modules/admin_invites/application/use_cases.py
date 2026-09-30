from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..domain.entities import MAX_INVITE_TTL_HOURS, AdminInvite, InviteKind
from ..domain.repository import AdminInviteRepository
from .commands import (
    CreateAdminInviteCommand,
    RedeemAdminInviteCommand,
    RevokeAdminInviteCommand,
)
from .ports import InviteGrants, InviteTokenCodec


class AdminInviteNotFound(RuntimeError):
    pass


class AdminInviteInvalid(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CreatedAdminInvite:
    invite: AdminInvite
    raw_token: str


@dataclass(frozen=True, slots=True)
class RedeemedAdminInvite:
    invite: AdminInvite
    admin_id: int
    created: bool


class CreateAdminInvite:
    def __init__(self, repository: AdminInviteRepository, codec: InviteTokenCodec) -> None:
        self._repository = repository
        self._codec = codec

    def execute(self, command: CreateAdminInviteCommand, *, now: datetime) -> CreatedAdminInvite:
        if not 1 <= command.ttl_hours <= MAX_INVITE_TTL_HOURS:
            raise ValueError(f"TTL must be between 1 and {MAX_INVITE_TTL_HOURS} hours")
        invite = AdminInvite(
            id=None,
            kind=command.kind,
            bot_instance_id=command.bot_instance_id,
            full_name=command.full_name,
            staff_role=command.staff_role,
            permissions=command.permissions,
            max_uses=command.max_uses,
            used_count=0,
            expires_at=now + timedelta(hours=command.ttl_hours),
            created_by_admin_id=command.created_by_admin_id,
        )
        raw_token = self._codec.generate()
        stored = self._repository.add(invite, self._codec.digest(raw_token))
        return CreatedAdminInvite(invite=stored, raw_token=raw_token)


class ListAdminInvites:
    def __init__(self, repository: AdminInviteRepository) -> None:
        self._repository = repository

    def execute(self, kind: InviteKind, bot_instance_id: int | None) -> list[AdminInvite]:
        return self._repository.list(kind, bot_instance_id)


class RevokeAdminInvite:
    def __init__(self, repository: AdminInviteRepository) -> None:
        self._repository = repository

    def execute(self, command: RevokeAdminInviteCommand, *, now: datetime) -> AdminInvite:
        invite = self._repository.get(command.invite_id, command.kind, command.bot_instance_id)
        if invite is None or invite.id is None:
            raise AdminInviteNotFound(str(command.invite_id))
        if invite.revoked_at is not None:
            return invite
        return self._repository.revoke(invite.id, now)


class RedeemAdminInvite:
    def __init__(
        self,
        repository: AdminInviteRepository,
        codec: InviteTokenCodec,
        grants: InviteGrants,
    ) -> None:
        self._repository = repository
        self._codec = codec
        self._grants = grants

    def execute(self, command: RedeemAdminInviteCommand, *, now: datetime) -> RedeemedAdminInvite:
        invite = self._repository.get_by_token_hash_for_update(
            self._codec.digest(command.raw_token)
        )
        if invite is None or invite.id is None or invite.status(now) != "active":
            raise AdminInviteInvalid

        if invite.kind == "platform":
            outcome = self._grants.grant_platform_admin(command.max_user_id, invite.full_name)
        else:
            if invite.bot_instance_id is None or invite.staff_role is None or invite.permissions is None:
                raise AdminInviteInvalid
            outcome = self._grants.grant_bot_staff(
                invite.bot_instance_id,
                command.max_user_id,
                invite.full_name,
                invite.staff_role,
                invite.permissions,
            )

        used = self._repository.increment_used(invite.id)
        return RedeemedAdminInvite(invite=used, admin_id=outcome.admin_id, created=outcome.created)
