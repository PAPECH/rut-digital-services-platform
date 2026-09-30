from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from ...profiles.domain.fields import CORE_PROFILE_KEYS, DIRECT_OPTIONAL_PROFILE_KEYS


class BrandingSettings(BaseModel):
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    logo_url: str | None = Field(default=None, max_length=1000)


class BottomNavigationItemSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["category", "submission_history", "form_catalog"] = "category"
    category_slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    label: str = Field(min_length=1, max_length=24)
    icon: Literal[
        "folder",
        "document",
        "info",
        "star",
        "contact",
        "building",
        "calendar",
        "book",
        "map",
        "users",
        "briefcase",
        "help-circle",
    ] = "folder"

    @model_validator(mode="after")
    def validate_target(self) -> "BottomNavigationItemSettings":
        if self.target == "category" and self.category_slug is None:
            raise ValueError("Category navigation target requires category_slug")
        if self.target != "category" and self.category_slug is not None:
            raise ValueError("System navigation target cannot contain category_slug")
        return self


class BottomNavigationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    custom_items: list[BottomNavigationItemSettings] = Field(default_factory=list, max_length=2)

    @field_validator("custom_items")
    @classmethod
    def unique_targets(
        cls,
        value: list[BottomNavigationItemSettings],
    ) -> list[BottomNavigationItemSettings]:
        targets = [
            f"category:{item.category_slug}" if item.target == "category" else item.target
            for item in value
        ]
        if len(targets) != len(set(targets)):
            raise ValueError("Bottom navigation targets must be unique")
        return value


ProfileDisplayFieldKey = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9_.-]{0,79}$"),
]


class SubmissionTableSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_fields: list[ProfileDisplayFieldKey] = Field(
        default_factory=lambda: ["full_name", "phone", "email", "birth_date"],
        max_length=100,
    )

    @field_validator("profile_fields")
    @classmethod
    def unique_profile_fields(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Submission table profile fields must be unique")
        return value


class ChatSettings(BaseModel):
    """Управляет тем, принимает ли бот свободный текст от студента вообще —
    выключается для ботов без поддержки/базы знаний (например, чисто
    информационных), которым текстовые сообщения не нужны."""

    model_config = ConfigDict(extra="forbid")

    student_text_enabled: bool = True


class KnowledgeBaseSettings(BaseModel):
    """Переопределения порогов семантического матчинга
    (modules/knowledge_base/application/use_cases.py::MatchKnowledgeBase) для
    конкретного бота. None означает «использовать платформенное значение по
    умолчанию» (core/config.py Settings.KB_*)."""

    model_config = ConfigDict(extra="forbid")

    auto_answer_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    candidate_min_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    max_candidates: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "KnowledgeBaseSettings":
        if (
            self.auto_answer_threshold is not None
            and self.candidate_min_threshold is not None
            and self.candidate_min_threshold > self.auto_answer_threshold
        ):
            raise ValueError("candidate_min_threshold must not exceed auto_answer_threshold")
        return self


class ProfileSettings(BaseModel):
    """Per-bot visibility of the mini-app's «Профиль» tab (Task 054) — off only for bots an
    admin explicitly turns it off for; default stays on, preserving today's behavior for
    every existing bot. Enforced bidirectionally against profile_schema/installed
    capabilities at write time (see UpdateBotInstance/CreateBotInstance), not by blocking
    GET/PUT /profile at request time — see docs/tasks/054-configurable-profile-tab.md's
    "Rejected design" note for why the latter would break session auth."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


class BotSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bottom_navigation: BottomNavigationSettings = Field(default_factory=BottomNavigationSettings)
    submission_table: SubmissionTableSettings = Field(default_factory=SubmissionTableSettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    profile: ProfileSettings = Field(default_factory=ProfileSettings)


class ProfileFieldDefinition(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,79}$")
    label: str = Field(min_length=1, max_length=200)
    type: Literal["string", "email", "phone", "boolean", "date", "number", "select"] = "string"
    required: bool = False
    shared: bool = False
    options: list[str] | None = None

    @field_validator("key")
    @classmethod
    def reject_core_field(cls, value: str) -> str:
        if value in CORE_PROFILE_KEYS:
            raise ValueError("Core profile fields are managed by the platform")
        return value

    @model_validator(mode="after")
    def validate_options(self) -> "ProfileFieldDefinition":
        if self.type == "select" and not self.options:
            raise ValueError("Select profile field requires options")
        return self

    @model_validator(mode="after")
    def reject_unmarked_direct_optional_field(self) -> "ProfileFieldDefinition":
        # study_group/job_title/structural_unit always route to the shared User
        # column (DIRECT_OPTIONAL_PROFILE_KEYS), regardless of this flag — so
        # declaring one of them with shared: false is a lie about actual behavior.
        if self.key in DIRECT_OPTIONAL_PROFILE_KEYS and not self.shared:
            raise ValueError(
                f"'{self.key}' is a platform-managed shared field; declare it with shared: true"
            )
        return self


class BotInstanceCreateRequest(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_active: bool = True
    order: int = 0
    branding: BrandingSettings = Field(default_factory=BrandingSettings)
    settings: BotSettings = Field(default_factory=BotSettings)
    profile_schema: list[ProfileFieldDefinition] = Field(default_factory=list)
    bot_token: SecretStr = Field(min_length=1)


class BotInstancePatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    is_active: bool | None = None
    order: int | None = None
    branding: BrandingSettings | None = None
    settings: BotSettings | None = None
    profile_schema: list[ProfileFieldDefinition] | None = None


class BotInstanceResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    is_active: bool
    order: int
    branding: dict[str, Any]
    settings: BotSettings
    profile_schema: list[dict[str, Any]]
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
