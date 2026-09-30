from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HeadingBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["heading"]
    text: str = Field(min_length=1, max_length=300)
    level: Literal[1, 2, 3, 4, 5, 6]


class RichTextRun(StrictModel):
    text: str = Field(min_length=1, max_length=2_000)
    marks: list[Literal["bold", "italic", "underline", "strike"]] = Field(default_factory=list)
    href: str | None = Field(default=None, max_length=2_000)


class RichTextParagraphNode(StrictModel):
    type: Literal["paragraph"]
    runs: list[RichTextRun] = Field(min_length=1, max_length=200)


class RichTextListNode(StrictModel):
    type: Literal["bullet_list", "ordered_list"]
    items: list[list[RichTextRun]] = Field(min_length=1, max_length=100)


RichTextNodeSchema = Annotated[
    RichTextParagraphNode | RichTextListNode,
    Field(discriminator="type"),
]


class RichTextDoc(StrictModel):
    format: Literal["rich_text_v1"]
    nodes: list[RichTextNodeSchema] = Field(min_length=1, max_length=300)


# A `paragraph`/`callout` block's text is either a legacy plain string (unformatted) or the typed
# rich-text document the admin's WYSIWYG editor writes -- mirrors
# `content_blocks.domain.rich_text`. Length/emptiness for the plain-string branch is enforced by
# the domain layer's own validator, not duplicated here, since a bare `str | Model` union can't
# carry per-branch Field constraints.
FormattedText = str | RichTextDoc


class ParagraphBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["paragraph"]
    text: FormattedText


class CalloutBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["callout"]
    title: str | None = Field(default=None, max_length=300)
    text: FormattedText
    tone: Literal["info", "warning", "success", "danger"]


class ContactItem(StrictModel):
    label: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=500)
    href: str | None = Field(default=None, max_length=2_000)


class ContactListBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["contact_list"]
    items: list[ContactItem] = Field(min_length=1, max_length=30)


class TitledItem(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=5_000)


class AccordionBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["accordion"]
    items: list[TitledItem] = Field(min_length=1, max_length=50)


class StepsBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["steps"]
    items: list[TitledItem] = Field(min_length=1, max_length=50)


class LinkBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["link"]
    title: str = Field(min_length=1, max_length=300)
    href: str = Field(min_length=1, max_length=2_000)
    style: Literal["card", "button"]
    external: bool


class FileItem(StrictModel):
    attachment_id: PositiveInt
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=1_000)
    display_mode: Literal["tile", "inline_image"] = "tile"


class FileListBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["file_list"]
    items: list[FileItem] = Field(min_length=1, max_length=30)


class FormActionBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["form_action"]
    form_id: PositiveInt
    title: str | None = Field(default=None,max_length=300)
    description: str | None = Field(default=None, max_length=1_000)


class TestActionBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["test_action"]
    test_id: PositiveInt
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=1_000)


class CapabilityActionBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["capability_action"]
    capability_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    view_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=1_000)


class CategoryGridBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["category_grid"]
    parent_id: PositiveInt | None = None
    title: str | None = Field(default=None, max_length=300)


class FormCatalogBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["form_catalog"]
    title: str | None = Field(default=None, max_length=300)


class SubmissionHistoryBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["submission_history"]
    title: str | None = Field(default=None, max_length=300)


class TestCatalogBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["test_catalog"]
    title: str | None = Field(default=None, max_length=300)


class TestAttemptHistoryBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["test_attempt_history"]
    title: str | None = Field(default=None, max_length=300)


class FaqListBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["faq_list"]
    title: str | None = Field(default=None, max_length=300)


class NewsListBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["news_list"]
    title: str | None = Field(default=None, max_length=300)


NestedContentBlock = Annotated[
    HeadingBlock
    | ParagraphBlock
    | CalloutBlock
    | ContactListBlock
    | AccordionBlock
    | StepsBlock
    | LinkBlock
    | FileListBlock
    | FormActionBlock
    | TestActionBlock
    | CapabilityActionBlock,
    Field(discriminator="type"),
]


class TabItem(StrictModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=200)
    blocks: list[NestedContentBlock] = Field(max_length=30)


class TabsBlock(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    type: Literal["tabs"]
    tabs: list[TabItem] = Field(min_length=1, max_length=12)


ContentBlock = Annotated[
    NestedContentBlock
    | TabsBlock
    | CategoryGridBlock
    | FormCatalogBlock
    | SubmissionHistoryBlock
    | TestCatalogBlock
    | TestAttemptHistoryBlock
    | FaqListBlock
    | NewsListBlock,
    Field(discriminator="type"),
]


class CategoryCreateRequest(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    icon: str = Field(default="folder", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=2_000)
    language: str = Field(default="ru", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    order: int = Field(default=0, ge=0, le=100_000)
    parent_id: PositiveInt | None = None
    # Both set -> a capability shortcut instead of a content page (Task 044); both-or-neither
    # enforced by the use case, not here, so a partial pair surfaces as a stable error code
    # instead of a generic 422.
    capability_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,63}$")
    capability_view_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    image_url: str | None = Field(default=None, max_length=2_000)


class CategoryPatchRequest(StrictModel):
    icon: str | None = Field(default=None, min_length=1, max_length=80)
    order: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
    parent_id: PositiveInt | None = None
    # Card fields, editable only for an existing capability shortcut -- see UpdateContentCategory.
    title: str | None = Field(default=None, min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=2_000)
    image_url: str | None = Field(default=None, max_length=2_000)


class DraftSaveRequest(StrictModel):
    expected_revision: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=2_000)
    language: str = Field(default="ru", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    blocks: list[ContentBlock] = Field(max_length=80)
    is_shared: bool = False
    is_filled: bool = False
    image_url: str | None = None
    header_visible: bool = True


class PublishRequest(StrictModel):
    expected_revision: int = Field(ge=0)


class ReorderRequest(StrictModel):
    category_ids: list[PositiveInt] = Field(max_length=500)


class DraftResponse(StrictModel):
    category_id: int
    title: str
    subtitle: str | None
    language: str
    blocks: list[ContentBlock]
    revision: int
    is_shared: bool
    is_filled: bool
    image_url: str | None
    header_visible: bool


class AdminCategoryResponse(StrictModel):
    id: int
    slug: str
    parent_id: int | None
    icon: str
    order: int
    is_active: bool
    published_version_id: int | None
    last_published_revision: int
    is_home: bool
    # None for a capability shortcut, which has no draft.
    draft: DraftResponse | None
    capability_key: str | None
    capability_view_key: str | None
    title: str | None
    subtitle: str | None
    image_url: str | None


class PublishedCategorySummaryResponse(StrictModel):
    id: int
    slug: str
    parent_id: int | None
    icon: str
    order: int
    title: str
    subtitle: str | None
    # None for a capability shortcut, which has no published version.
    version_id: int | None
    version: int | None
    is_filled: bool
    image_url: str | None
    header_visible: bool
    is_home: bool
    capability_key: str | None
    capability_view_key: str | None


class AttachmentUrlEntry(StrictModel):
    url: str
    mime: str


class PublishedContentResponse(PublishedCategorySummaryResponse):
    language: str
    blocks: list[ContentBlock]
    attachment_urls: dict[int, AttachmentUrlEntry] = Field(default_factory=dict)
    published_at: datetime


class PreviewTokenResponse(StrictModel):
    token: str
    expires_at: datetime


class DraftPreviewResponse(StrictModel):
    content: PublishedContentResponse
    preview_access_token: str
    bot_slug: str
    expires_at: datetime


class ContentOpenEventRequest(StrictModel):
    category_id: PositiveInt
    version_id: PositiveInt


class ContentTabOpenEventRequest(ContentOpenEventRequest):
    tab_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ContentAttachmentReferenceResponse(StrictModel):
    category_id: int
    usage: Literal["card_image", "file_list_item"]


class ContentAttachmentResponse(StrictModel):
    id: int
    name: str
    mime: str
    size_bytes: int
    url: str
    created_at: datetime
    referenced_by_draft: list[ContentAttachmentReferenceResponse]
    referenced_by_published: list[ContentAttachmentReferenceResponse]


class ContentAttachmentListResponse(StrictModel):
    items: list[ContentAttachmentResponse]
    total: int


class ContentFormOptionResponse(StrictModel):
    id: int
    name: str


class ContentTestOptionResponse(StrictModel):
    id: int
    name: str


class SharedContentDraftResponse(StrictModel):
    source_category_id: int
    source_bot_instance_id: int
    source_bot_name: str
    slug: str
    title: str
    subtitle: str | None
    icon: str
    language: str


class FormDependencyTargetResponse(StrictModel):
    kind: Literal["form"] = "form"
    id: int
    slug: str
    label: str


class SharedContentFormDependencyResponse(StrictModel):
    kind: Literal["form"] = "form"
    source_id: int
    source_slug: str | None
    label: str
    status: Literal["resolved", "copy_available", "mapping_required", "unavailable"]
    can_copy: bool
    matched_target_id: int | None
    matched_target_ready: bool


class ContentDependencyBlockerResponse(StrictModel):
    kind: Literal["file"]
    code: Literal["file_copy_not_supported"]
    count: int = Field(ge=1)


class SharedContentDependenciesResponse(StrictModel):
    dependencies: list[SharedContentFormDependencyResponse]
    targets: list[FormDependencyTargetResponse]
    blockers: list[ContentDependencyBlockerResponse]


class UseExistingFormResolutionRequest(StrictModel):
    kind: Literal["form"]
    source_id: PositiveInt
    action: Literal["use_existing"]
    target_id: PositiveInt


class CopySharedFormResolutionRequest(StrictModel):
    kind: Literal["form"]
    source_id: PositiveInt
    action: Literal["copy_shared"]


FormDependencyResolutionRequest = Annotated[
    UseExistingFormResolutionRequest | CopySharedFormResolutionRequest,
    Field(discriminator="action"),
]


class SharedContentDraftImportRequest(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    parent_id: PositiveInt | None = None
    order: int = Field(default=0, ge=0, le=100_000)
    resolutions: list[FormDependencyResolutionRequest] = Field(default_factory=list, max_length=200)


class ResolvedFormDependencyResponse(StrictModel):
    kind: Literal["form"] = "form"
    source_id: int
    target_id: int
    action: Literal["matched_slug", "use_existing", "copy_shared"]
    target_ready: bool


class SharedContentDraftImportResponse(StrictModel):
    category: AdminCategoryResponse
    dependencies: list[ResolvedFormDependencyResponse]
