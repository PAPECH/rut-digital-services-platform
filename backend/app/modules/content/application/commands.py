from dataclasses import dataclass
from typing import Any

from .dependencies import FormDependencyResolution


@dataclass(frozen=True, slots=True)
class CreateCategoryCommand:
    bot_instance_id: int
    slug: str
    icon: str
    title: str
    subtitle: str | None
    language: str
    order: int
    created_by: int | None
    parent_id: int | None = None
    # Both set -> a capability shortcut instead of a content page; both-or-neither enforced by
    # the use case. `image_url` is the shortcut's own card image (a shortcut has no draft to
    # carry one).
    capability_key: str | None = None
    capability_view_key: str | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateCategoryCommand:
    bot_instance_id: int
    category_id: int
    icon: str | None = None
    order: int | None = None
    is_active: bool | None = None
    parent_id: int | None = None
    change_parent: bool = False
    # Editable only when the category is already a capability shortcut; repointing
    # capability_key/capability_view_key themselves is out of scope (delete/recreate instead).
    title: str | None = None
    subtitle: str | None = None
    change_subtitle: bool = False
    image_url: str | None = None
    change_image: bool = False


@dataclass(frozen=True, slots=True)
class SaveDraftCommand:
    bot_instance_id: int
    category_id: int
    expected_revision: int
    title: str
    subtitle: str | None
    language: str
    blocks: list[dict[str, Any]]
    updated_by: int | None
    is_shared: bool = False
    is_filled: bool = False
    image_url: str | None = None
    header_visible: bool = True


@dataclass(frozen=True, slots=True)
class PublishContentCommand:
    bot_instance_id: int
    category_id: int
    expected_revision: int
    published_by: int | None


@dataclass(frozen=True, slots=True)
class ImportSharedContentDraftCommand:
    bot_instance_id: int
    source_category_id: int
    slug: str
    parent_id: int | None
    order: int
    created_by: int | None
    form_resolutions: tuple[FormDependencyResolution, ...] = ()
    can_copy_forms: bool = False
