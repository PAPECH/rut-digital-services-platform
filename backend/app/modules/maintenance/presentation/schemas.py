from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ...bot_instances.presentation.schemas import BotSettings
from ...capabilities.presentation.schemas import PublicCapabilityResponse
from ..domain.policies import MaintenanceMode, MaintenancePolicy


class MaintenancePatchRequest(BaseModel):
    mode: MaintenanceMode
    title: str = Field(default="", max_length=240)
    message: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    retry_after_seconds: int | None = Field(default=None, ge=0)
    allow_admin: bool = True


class MaintenanceResponse(BaseModel):
    scope_key: str
    bot_instance_id: int | None
    mode: MaintenanceMode
    title: str
    message: str
    starts_at: datetime | None
    ends_at: datetime | None
    retry_after_seconds: int | None
    allow_admin: bool

    @classmethod
    def from_domain(cls, policy: MaintenancePolicy) -> "MaintenanceResponse":
        return cls(
            scope_key=policy.scope_key,
            bot_instance_id=policy.bot_instance_id,
            mode=policy.mode,
            title=policy.title,
            message=policy.message,
            starts_at=policy.starts_at,
            ends_at=policy.ends_at,
            retry_after_seconds=policy.retry_after_seconds,
            allow_admin=policy.allow_admin,
        )


class ManifestBot(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    branding: dict[str, Any]
    settings: BotSettings
    profile_schema: list[dict[str, Any]]


class AppManifestResponse(BaseModel):
    bot: ManifestBot
    maintenance: MaintenanceResponse | None
    capabilities: list[PublicCapabilityResponse] = Field(default_factory=list)
