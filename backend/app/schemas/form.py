from datetime import datetime

from pydantic import BaseModel, Field

from ..models.enums import FieldTypeEnum


class FormFieldIn(BaseModel):
    label: str
    type: FieldTypeEnum
    regexp: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    default_value: str | None = None
    is_active: bool = True
    is_required: bool = False
    order: int = 0
    profile_key: str | None = None
    meta: dict | None = None


class FormFieldOut(FormFieldIn):
    id: int

    model_config = {"from_attributes": True}


class FormTemplateIn(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    order: int = 0
    reply_on_accept: str | None = None


class FormTemplateOut(FormTemplateIn):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FormTemplateDetailed(FormTemplateOut):
    fields: list[FormFieldOut] = Field(default_factory=list)


class FormTemplatePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    order: int | None = None
    reply_on_accept: str | None = None


class FormFieldPatch(BaseModel):
    label: str | None = None
    type: FieldTypeEnum | None = None
    regexp: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    default_value: str | None = None
    is_active: bool | None = None
    is_required: bool | None = None
    order: int | None = None
    profile_key: str | None = None
    meta: dict | None = None
