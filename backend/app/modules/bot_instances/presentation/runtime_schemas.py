from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class RuntimePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential_env_key: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]{0,119}$",
    )
    mode: Literal["polling", "webhook"] = "polling"


class RuntimeCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["environment", "managed"]
    credential_env_key: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]{0,119}$",
    )
    bot_token: SecretStr | None = None
    mode: Literal["polling", "webhook"] = "polling"

    @model_validator(mode="after")
    def validate_source_fields(self) -> "RuntimeCredentialRequest":
        if self.source == "environment" and not self.credential_env_key:
            raise ValueError("Environment credential source requires an env key")
        if self.source == "managed" and self.credential_env_key is not None:
            raise ValueError("Managed credential source assigns its own env key")
        return self


class RuntimeHeartbeatRequest(BaseModel):
    username: str | None = Field(default=None, max_length=120)
    user_id: str | None = Field(default=None, max_length=120)
    version: str | None = Field(default=None, max_length=120)
    error_code: str | None = Field(default=None, max_length=120)


class RuntimeResponse(BaseModel):
    bot_instance_id: int
    credential_source: Literal["environment", "managed"] | None
    credential_env_key: str | None
    mode: Literal["polling", "webhook"]
    bot_token_configured: bool
    token_configured: bool
    status: Literal["online", "offline", "error", "not_connected"]
    last_seen_at: datetime | None
    username: str | None
    max_bot_id: str | None
    runtime_version: str | None
    last_error_code: str | None


class RuntimeTokenResponse(BaseModel):
    runtime_token: str


class BotProcessManifestItem(BaseModel):
    bot_instance_id: int
    slug: str
    credential_env_key: str | None
    mode: Literal["polling", "webhook"]
    runtime_token_configured: bool
