from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ....core.config import settings
from ...bot_instances.presentation.staff_access_schemas import StaffPermissionsSchema
from ..application.use_cases import CreatedAdminInvite
from ..domain.entities import MAX_INVITE_TTL_HOURS, MAX_INVITE_USES, AdminInvite
from ..domain.start_param import invite_start_param


class _InviteLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    ttl_hours: int = Field(default=168, ge=1, le=MAX_INVITE_TTL_HOURS)
    max_uses: int = Field(default=1, ge=1, le=MAX_INVITE_USES)


class CreatePlatformInviteRequest(_InviteLimits):
    pass


class CreateBotInviteRequest(_InviteLimits):
    role: Literal["employee", "admin"] = "employee"
    permissions: StaffPermissionsSchema = Field(default_factory=StaffPermissionsSchema)


class AdminInviteResponse(BaseModel):
    id: int
    kind: Literal["platform", "bot_staff"]
    full_name: str
    role: Literal["employee", "admin"] | None
    permissions: StaffPermissionsSchema | None
    max_uses: int
    used_count: int
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime | None
    status: Literal["active", "expired", "exhausted", "revoked"]

    @classmethod
    def from_domain(cls, invite: AdminInvite) -> AdminInviteResponse:
        if invite.id is None:
            raise ValueError("Invite must be persisted")
        return cls(
            id=invite.id,
            kind=invite.kind,
            full_name=invite.full_name,
            role=invite.staff_role,
            permissions=(
                StaffPermissionsSchema(**asdict(invite.permissions)) if invite.permissions else None
            ),
            max_uses=invite.max_uses,
            used_count=invite.used_count,
            expires_at=invite.expires_at,
            revoked_at=invite.revoked_at,
            created_at=invite.created_at,
            status=invite.status(datetime.now(tz=UTC)),
        )


class CreatedAdminInviteResponse(BaseModel):
    invite: AdminInviteResponse
    start_param: str
    link: str | None

    @classmethod
    def from_result(cls, result: CreatedAdminInvite) -> CreatedAdminInviteResponse:
        start_param = invite_start_param(result.raw_token)
        username = settings.MAX_BOT_USERNAME.strip().lstrip("@")
        return cls(
            invite=AdminInviteResponse.from_domain(result.invite),
            start_param=start_param,
            link=f"https://max.ru/{username}?startapp={start_param}" if username else None,
        )
