from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..application.use_cases import EnsurePlatformAdminResult
from ..domain.entities import GlobalAdminIdentity


class EnsurePlatformAdminRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_user_id: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)


class PlatformAdminResponse(BaseModel):
    id: int
    max_user_id: str
    full_name: str
    is_active: bool

    @classmethod
    def from_domain(cls, identity: GlobalAdminIdentity) -> PlatformAdminResponse:
        if identity.id is None:
            raise ValueError("Platform administrator must be persisted")
        return cls(
            id=identity.id,
            max_user_id=identity.max_user_id,
            full_name=identity.full_name,
            is_active=identity.is_active,
        )


class EnsurePlatformAdminResponse(BaseModel):
    account: PlatformAdminResponse
    created: bool
    promoted: bool
    reactivated: bool

    @classmethod
    def from_result(cls, result: EnsurePlatformAdminResult) -> EnsurePlatformAdminResponse:
        return cls(
            account=PlatformAdminResponse.from_domain(result.identity),
            created=result.created,
            promoted=result.previous_role not in {None, "platform_admin"},
            reactivated=result.reactivated,
        )
