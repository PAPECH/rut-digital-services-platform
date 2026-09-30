from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityViewResponse(StrictModel):
    key: str
    title: str
    subtitle: str | None
    icon: str
    path: str
    requires_complete_profile: bool


class CapabilityDescriptorResponse(StrictModel):
    key: str
    version: str
    name: str
    description: str
    admin_editor_key: str
    views: list[CapabilityViewResponse]


class CapabilityInstallationResponse(StrictModel):
    id: int | None
    bot_instance_id: int
    capability_key: str
    version: str
    name: str
    description: str
    admin_editor_key: str
    is_enabled: bool
    order: int
    config: dict[str, Any]
    config_revision: int
    last_health_status: str
    last_health_at: datetime | None
    last_health_error_code: str | None
    views: list[CapabilityViewResponse]


class CapabilityConfigRequest(StrictModel):
    expected_revision: int = Field(ge=0)
    config: dict[str, Any]


class CapabilityReorderRequest(StrictModel):
    capability_keys: list[str] = Field(max_length=100)


class PublicCapabilityResponse(StrictModel):
    installation_id: int
    key: str
    version: str
    views: list[CapabilityViewResponse]
    public_config: dict[str, Any]


class CapabilityViewOpenRequest(StrictModel):
    installation_id: int = Field(gt=0)
    view_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
