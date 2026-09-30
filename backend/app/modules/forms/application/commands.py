from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CreateFormCommand:
    bot_instance_id: int
    slug: str
    name: str
    description: str | None
    reply_on_accept: str | None
    order: int
    created_by: int | None


@dataclass(frozen=True, slots=True)
class UpdateFormCommand:
    bot_instance_id: int
    form_id: int
    order: int | None = None
    is_active: bool | None = None
    show_in_catalog: bool | None = None
    is_archived: bool | None = None


@dataclass(frozen=True, slots=True)
class SaveFormDraftCommand:
    bot_instance_id: int
    form_id: int
    expected_revision: int
    name: str
    description: str | None
    reply_on_accept: str | None
    fields: list[dict[str, Any]]
    updated_by: int | None
    is_shared: bool = False


@dataclass(frozen=True, slots=True)
class PublishFormCommand:
    bot_instance_id: int
    form_id: int
    expected_revision: int
    published_by: int | None


@dataclass(frozen=True, slots=True)
class ImportSharedFormDraftCommand:
    bot_instance_id: int
    source_form_id: int
    slug: str
    order: int
    created_by: int | None
