from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class FormDefinition:
    id: int | None
    bot_instance_id: int
    slug: str
    order: int = 0
    is_active: bool = False
    show_in_catalog: bool = True
    is_archived: bool = False
    published_version_id: int | None = None
    last_published_revision: int = -1


@dataclass(frozen=True, slots=True)
class FormDraft:
    form_definition_id: int
    name: str
    description: str | None = None
    reply_on_accept: str | None = None
    fields: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 0
    is_shared: bool = False


@dataclass(frozen=True, slots=True)
class SharedFormDraft:
    source_bot_instance_id: int
    source_bot_name: str
    definition: FormDefinition
    draft: FormDraft


@dataclass(frozen=True, slots=True)
class FormVersion:
    id: int | None
    form_definition_id: int
    version: int
    source_revision: int
    name: str
    description: str | None
    reply_on_accept: str | None
    fields: list[dict[str, Any]]
    published_by: int | None
    published_at: datetime


@dataclass(frozen=True, slots=True)
class PublishedForm:
    definition: FormDefinition
    version: FormVersion
