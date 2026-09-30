from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldBase(StrictModel):
    key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    label: str = Field(min_length=1, max_length=300)
    help_text: str | None = Field(default=None, max_length=2_000)
    required: bool = False
    active: bool = True
    profile_key: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")


class ShortTextField(FieldBase):
    type: Literal["short_text"]
    placeholder: str | None = Field(default=None, max_length=500)
    default: str | None = Field(default=None, max_length=20_000)
    min_length: int = Field(default=0, ge=0, le=20_000)
    max_length: int = Field(default=20_000, ge=1, le=20_000)
    pattern: str | None = Field(default=None, max_length=500)


class LongTextField(FieldBase):
    type: Literal["long_text"]
    placeholder: str | None = Field(default=None, max_length=500)
    default: str | None = Field(default=None, max_length=20_000)
    min_length: int = Field(default=0, ge=0, le=20_000)
    max_length: int = Field(default=20_000, ge=1, le=20_000)


class EmailField(FieldBase):
    type: Literal["email"]
    placeholder: str | None = Field(default=None, max_length=500)
    default: str | None = Field(default=None, max_length=320)


class PhoneField(FieldBase):
    type: Literal["phone"]
    placeholder: str | None = Field(default=None, max_length=500)
    default: str | None = Field(default=None, max_length=100)
    pattern: str | None = Field(default=None, max_length=500)


class NumberField(FieldBase):
    type: Literal["number"]
    placeholder: str | None = Field(default=None, max_length=500)
    default: float | int | None = None
    min: float | int | None = None
    max: float | int | None = None
    step: float | int = Field(default=1, gt=0)


class DateField(FieldBase):
    type: Literal["date"]
    default: str | None = None
    min: str | None = None
    max: str | None = None


class CheckboxField(FieldBase):
    type: Literal["checkbox"]
    default: bool = False


class FormOption(StrictModel):
    value: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=300)


class SelectField(FieldBase):
    type: Literal["select"]
    options: list[FormOption] = Field(min_length=1, max_length=100)
    default: str | None = Field(default=None, max_length=100)


class RadioField(FieldBase):
    type: Literal["radio"]
    options: list[FormOption] = Field(min_length=1, max_length=100)
    default: str | None = Field(default=None, max_length=100)


class MultiselectField(FieldBase):
    type: Literal["multiselect"]
    options: list[FormOption] = Field(min_length=1, max_length=100)
    default: list[str] | None = None
    min_selected: int | None = Field(default=None, ge=0)
    max_selected: int | None = Field(default=None, ge=0)


class FileField(FieldBase):
    type: Literal["file"]
    accepted_mime_types: list[str] = Field(default_factory=list, max_length=30)
    max_files: int = Field(default=1, ge=1, le=10)
    max_size_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=20 * 1024 * 1024)


FormField = Annotated[
    ShortTextField
    | LongTextField
    | EmailField
    | PhoneField
    | NumberField
    | DateField
    | CheckboxField
    | SelectField
    | RadioField
    | MultiselectField
    | FileField,
    Field(discriminator="type"),
]


class FormCreateRequest(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    name: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5_000)
    reply_on_accept: str | None = Field(default=None, max_length=5_000)
    order: int = Field(default=0, ge=0, le=100_000)


class FormPatchRequest(StrictModel):
    order: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
    show_in_catalog: bool | None = None
    is_archived: bool | None = None


class FormDraftSaveRequest(StrictModel):
    expected_revision: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5_000)
    reply_on_accept: str | None = Field(default=None, max_length=5_000)
    fields: list[FormField] = Field(max_length=100)
    is_shared: bool = False


class FormPublishRequest(StrictModel):
    expected_revision: int = Field(ge=0)


class FormReorderRequest(StrictModel):
    form_ids: list[PositiveInt] = Field(max_length=500)


class FormDraftResponse(StrictModel):
    form_id: int
    name: str
    description: str | None
    reply_on_accept: str | None
    fields: list[FormField]
    revision: int
    is_shared: bool


class AdminFormResponse(StrictModel):
    id: int
    slug: str
    order: int
    is_active: bool
    show_in_catalog: bool
    is_archived: bool
    published_version_id: int | None
    last_published_revision: int
    draft: FormDraftResponse


class PublishedFormSummaryResponse(StrictModel):
    id: int
    slug: str
    order: int
    name: str
    description: str | None
    version_id: int
    version: int


class PublishedFormResponse(PublishedFormSummaryResponse):
    reply_on_accept: str | None
    fields: list[FormField]
    published_at: datetime


class SharedFormDraftResponse(StrictModel):
    source_form_id: int
    source_bot_instance_id: int
    source_bot_name: str
    slug: str
    name: str
    description: str | None


class SharedFormDraftImportRequest(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    order: int = Field(default=0, ge=0, le=100_000)
