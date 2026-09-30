from __future__ import annotations

import re
from dataclasses import replace

from ..domain.blocks import (
    extract_capability_references,
    extract_category_references,
    extract_inline_image_attachment_ids,
    extract_references,
    extract_test_references,
    validate_blocks,
)
from ..domain.entities import (
    ContentAttachmentPage,
    ContentCategory,
    ContentDraft,
    ContentFormOption,
    ContentTestOption,
    DeletedAttachment,
    PublishedContent,
)
from ..domain.repositories import ContentRepository
from .commands import (
    CreateCategoryCommand,
    ImportSharedContentDraftCommand,
    PublishContentCommand,
    SaveDraftCommand,
    UpdateCategoryCommand,
)
from .dependencies import (
    ContentDependencyCopyForbidden,
    ContentDependencyResolutionInvalid,
    FormDependencyResolution,
    SharedContentDependencyReport,
    SharedContentImportResult,
)
from .ports import (
    ContentAnalyticsGateway,
    ContentAssetCatalog,
    ContentReferenceGateway,
    ContentTemplateDependencyGateway,
)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
# Mirrors `domain.blocks`' capability_action validation and `modules.capabilities.domain.entities`
# (duplicated across those layers already; matching that existing style rather than introducing a
# shared constant).
CAPABILITY_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
CAPABILITY_VIEW_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


class ContentNotFound(RuntimeError):
    pass


class ContentSlugExists(RuntimeError):
    pass


class DraftRevisionConflict(RuntimeError):
    pass


class NothingToPublish(RuntimeError):
    pass


class CrossTenantReference(RuntimeError):
    def __init__(
        self,
        *,
        form_ids: set[int],
        attachment_ids: set[int],
        capability_views: set[tuple[str, str]],
        category_ids: set[int] = frozenset(),
        test_ids: set[int] = frozenset(),
    ) -> None:
        super().__init__("Content contains missing or cross-tenant references")
        self.form_ids = form_ids
        self.attachment_ids = attachment_ids
        self.capability_views = capability_views
        self.category_ids = category_ids
        self.test_ids = test_ids


class ContentDependenciesNotReady(RuntimeError):
    def __init__(self, form_ids: set[int], test_ids: set[int] = frozenset()) -> None:
        super().__init__("Content contains forms or tests that are not published and active")
        self.form_ids = form_ids
        self.test_ids = test_ids


class PublishedVersionMismatch(RuntimeError):
    pass


class ContentTabNotFound(RuntimeError):
    pass


class InvalidCategoryParent(RuntimeError):
    pass


class ShortcutPointerIncomplete(RuntimeError):
    pass


class ShortcutCannotHaveChildren(RuntimeError):
    pass


class ContentIsCapabilityShortcut(RuntimeError):
    def __init__(self, capability_key: str, view_key: str) -> None:
        super().__init__("Category is a capability shortcut, not a content page")
        self.capability_key = capability_key
        self.view_key = view_key


class SharedContentContainsFiles(RuntimeError):
    pass


class InvalidInlineImageAttachment(RuntimeError):
    def __init__(self, attachment_ids: set[int]) -> None:
        super().__init__("file_list items with display_mode=inline_image must reference an image attachment")
        self.attachment_ids = attachment_ids


class ContentAttachmentNotFound(RuntimeError):
    pass


class ContentAttachmentInUse(RuntimeError):
    def __init__(self, category_ids: list[int]) -> None:
        super().__init__("Attachment is referenced by a published content version")
        self.category_ids = category_ids


def _validate_parent(
    repository: ContentRepository,
    *,
    bot_instance_id: int,
    category_id: int | None,
    parent_id: int | None,
) -> None:
    if parent_id is None:
        return
    if category_id is not None and parent_id == category_id:
        raise InvalidCategoryParent("Category cannot be its own parent")
    parent = repository.get_category(bot_instance_id, parent_id)
    if parent is None:
        raise InvalidCategoryParent("Parent category does not belong to this bot")
    if parent.is_shortcut:
        raise ShortcutCannotHaveChildren("A capability shortcut cannot have children")
    visited: set[int] = set()
    while parent is not None:
        if parent.id is None or parent.id in visited:
            raise InvalidCategoryParent("Category tree contains a cycle")
        if category_id is not None and parent.id == category_id:
            raise InvalidCategoryParent("Category cannot be moved below its descendant")
        visited.add(parent.id)
        parent = (
            repository.get_category(bot_instance_id, parent.parent_id)
            if parent.parent_id is not None
            else None
        )


def _validate_references(
    gateway: ContentReferenceGateway,
    *,
    bot_instance_id: int,
    blocks: list[dict],
) -> None:
    form_ids, attachment_ids = extract_references(blocks)
    capability_views = extract_capability_references(blocks)
    test_ids = extract_test_references(blocks)
    missing_forms = gateway.missing_form_ids(bot_instance_id, form_ids)
    missing_attachments = gateway.missing_attachment_ids(bot_instance_id, attachment_ids)
    missing_capability_views = gateway.missing_capability_views(bot_instance_id, capability_views)
    missing_tests = gateway.missing_test_ids(bot_instance_id, test_ids)
    if missing_forms or missing_attachments or missing_capability_views or missing_tests:
        raise CrossTenantReference(
            form_ids=missing_forms,
            attachment_ids=missing_attachments,
            capability_views=missing_capability_views,
            test_ids=missing_tests,
        )
    inline_image_ids = extract_inline_image_attachment_ids(blocks)
    if inline_image_ids:
        mime_types = gateway.attachment_mime_types(bot_instance_id, inline_image_ids)
        invalid = {
            attachment_id
            for attachment_id in inline_image_ids
            if not mime_types.get(attachment_id, "").startswith("image/")
        }
        if invalid:
            raise InvalidInlineImageAttachment(invalid)


def _validate_category_references(
    repository: ContentRepository,
    *,
    bot_instance_id: int,
    blocks: list[dict],
) -> None:
    """`category_grid.parent_id` must resolve to a category owned by this bot -- checked
    directly against the content repository rather than the reference gateway, since
    "does this category belong to this bot" is exactly what `get_category` already answers."""
    category_ids = extract_category_references(blocks)
    missing = {
        category_id
        for category_id in category_ids
        if repository.get_category(bot_instance_id, category_id) is None
    }
    if missing:
        raise CrossTenantReference(
            form_ids=set(),
            attachment_ids=set(),
            capability_views=set(),
            category_ids=missing,
        )


def _validate_publishable_references(
    gateway: ContentReferenceGateway,
    *,
    bot_instance_id: int,
    blocks: list[dict],
) -> None:
    form_ids, _ = extract_references(blocks)
    test_ids = extract_test_references(blocks)
    unready_forms = gateway.unready_form_ids(bot_instance_id, form_ids)
    unready_tests = gateway.unready_test_ids(bot_instance_id, test_ids)
    if unready_forms or unready_tests:
        raise ContentDependenciesNotReady(unready_forms, unready_tests)


class CreateContentCategory:
    def __init__(self, repository: ContentRepository, reference_gateway: ContentReferenceGateway) -> None:
        self._repository = repository
        self._reference_gateway = reference_gateway

    def execute(self, command: CreateCategoryCommand) -> tuple[ContentCategory, ContentDraft | None]:
        slug = command.slug.strip().lower()
        title = command.title.strip()
        if not SLUG_RE.fullmatch(slug):
            raise ValueError("Invalid category slug")
        if not title:
            raise ValueError("Category title cannot be empty")
        if self._repository.get_category_by_slug(command.bot_instance_id, slug):
            raise ContentSlugExists(slug)
        _validate_parent(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            category_id=None,
            parent_id=command.parent_id,
        )
        has_capability_key = bool(command.capability_key)
        has_view_key = bool(command.capability_view_key)
        if has_capability_key != has_view_key:
            raise ShortcutPointerIncomplete(
                "capability_key and capability_view_key must be supplied together"
            )
        icon = command.icon.strip() or "folder"
        if not has_capability_key:
            category = ContentCategory(
                id=None,
                bot_instance_id=command.bot_instance_id,
                slug=slug,
                icon=icon,
                parent_id=command.parent_id,
                order=command.order,
            )
            draft = ContentDraft(
                category_id=0,
                title=title,
                subtitle=command.subtitle.strip() if command.subtitle else None,
                language=command.language,
            )
            return self._repository.create_category(category, draft, created_by=command.created_by)

        capability_key = command.capability_key.strip()
        view_key = command.capability_view_key.strip()
        if not CAPABILITY_KEY_RE.fullmatch(capability_key):
            raise ValueError("Invalid capability key")
        if not CAPABILITY_VIEW_KEY_RE.fullmatch(view_key):
            raise ValueError("Invalid capability view key")
        missing = self._reference_gateway.missing_capability_views(
            command.bot_instance_id, {(capability_key, view_key)}
        )
        if missing:
            raise CrossTenantReference(form_ids=set(), attachment_ids=set(), capability_views=missing)
        category = ContentCategory(
            id=None,
            bot_instance_id=command.bot_instance_id,
            slug=slug,
            icon=icon,
            parent_id=command.parent_id,
            order=command.order,
            capability_key=capability_key,
            capability_view_key=view_key,
            title=title,
            subtitle=command.subtitle.strip() if command.subtitle else None,
            image_url=command.image_url,
        )
        return self._repository.create_category(category, None, created_by=command.created_by)


class GetOrCreateHomeCategory:
    """Lazily creates the bot's reserved home-screen singleton (idempotent), so both the admin
    category list and the public home-content read always have something to show. On first
    creation, seeds and immediately publishes content that replicates today's hardcoded
    greeting-plus-top-level-category-grid home screen, so cutover changes no bot's appearance."""

    HOME_SLUG = "system-home-screen"

    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, bot_name: str) -> tuple[ContentCategory, ContentDraft]:
        existing = self._repository.get_home_category(bot_instance_id)
        if existing is not None:
            assert existing.id is not None
            draft = self._repository.get_draft(bot_instance_id, existing.id)
            assert draft is not None
            return existing, draft

        category = ContentCategory(
            id=None,
            bot_instance_id=bot_instance_id,
            slug=self.HOME_SLUG,
            icon="home",
            is_home=True,
        )
        seed_draft = ContentDraft(
            category_id=0,
            title="Здравствуйте, {{ profile.first_name }}!",
            subtitle=f"Добро пожаловать в {bot_name}!" if bot_name else "Добро пожаловать!",
            blocks=[{"id": "category_grid_default", "type": "category_grid", "parent_id": None}],
            header_visible=True,
        )
        created_category, created_draft = self._repository.create_category(
            category, seed_draft, created_by=None
        )
        assert created_category.id is not None
        # A freshly created draft is revision 0; publish() requires last_published_revision to
        # be below the draft's revision, so re-save once (identical content) to reach revision 1
        # before publishing -- the singleton must have a live published version immediately.
        saved_draft = self._repository.save_draft(
            bot_instance_id,
            created_draft,
            expected_revision=0,
            updated_by=None,
        )
        published = self._repository.publish(
            bot_instance_id,
            created_category.id,
            expected_revision=saved_draft.revision,
            published_by=None,
        )
        return published.category, saved_draft


class ListContentCategories:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[tuple[ContentCategory, ContentDraft]]:
        return self._repository.list_categories(bot_instance_id)


class ListPublishedContent:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[PublishedContent]:
        return self._repository.list_published(bot_instance_id)


class ListSharedContentDrafts:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self):
        return self._repository.list_shared_drafts()


class GetSharedContentDependencies:
    def __init__(
        self,
        repository: ContentRepository,
        dependency_gateway: ContentTemplateDependencyGateway,
    ) -> None:
        self._repository = repository
        self._dependency_gateway = dependency_gateway

    def execute(
        self,
        *,
        bot_instance_id: int,
        source_category_id: int,
    ) -> SharedContentDependencyReport:
        shared = self._repository.get_shared_draft(source_category_id)
        if shared is None:
            raise ContentNotFound(str(source_category_id))
        return self._dependency_gateway.inspect(
            source_bot_instance_id=shared.source_bot_instance_id,
            target_bot_instance_id=bot_instance_id,
            blocks=shared.draft.blocks,
        )


class ImportSharedContentDraft:
    def __init__(
        self,
        repository: ContentRepository,
        reference_gateway: ContentReferenceGateway,
        dependency_gateway: ContentTemplateDependencyGateway,
    ) -> None:
        self._repository = repository
        self._reference_gateway = reference_gateway
        self._dependency_gateway = dependency_gateway

    def execute(
        self,
        command: ImportSharedContentDraftCommand,
    ) -> SharedContentImportResult:
        shared = self._repository.get_shared_draft(command.source_category_id)
        if shared is None:
            raise ContentNotFound(str(command.source_category_id))
        slug = command.slug.strip().lower()
        if not SLUG_RE.fullmatch(slug):
            raise ValueError("Invalid category slug")
        if self._repository.get_category_by_slug(command.bot_instance_id, slug):
            raise ContentSlugExists(slug)
        _validate_parent(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            category_id=None,
            parent_id=command.parent_id,
        )
        source_ids = [item.source_id for item in command.form_resolutions]
        if len(source_ids) != len(set(source_ids)):
            raise ContentDependencyResolutionInvalid("Duplicate form dependency resolution")
        report = self._dependency_gateway.inspect(
            source_bot_instance_id=shared.source_bot_instance_id,
            target_bot_instance_id=command.bot_instance_id,
            blocks=shared.draft.blocks,
        )
        provided_source_ids = set(source_ids)
        implicit_resolutions = tuple(
            FormDependencyResolution(
                source_id=dependency.source_id,
                action="copy_shared",
            )
            for dependency in report.form_dependencies
            if dependency.source_id not in provided_source_ids
            and dependency.matched_target_id is None
            and dependency.source_is_shared
            and command.can_copy_forms
        )
        effective_resolutions = command.form_resolutions + implicit_resolutions
        if any(item.action == "copy_shared" for item in effective_resolutions):
            if not command.can_copy_forms:
                raise ContentDependencyCopyForbidden
        resolved = self._dependency_gateway.resolve(
            source_bot_instance_id=shared.source_bot_instance_id,
            target_bot_instance_id=command.bot_instance_id,
            blocks=shared.draft.blocks,
            form_resolutions=effective_resolutions,
            created_by=command.created_by,
        )
        category, _ = CreateContentCategory(self._repository, self._reference_gateway).execute(
            CreateCategoryCommand(
                bot_instance_id=command.bot_instance_id,
                slug=command.slug,
                icon=shared.category.icon,
                title=shared.draft.title,
                subtitle=shared.draft.subtitle,
                language=shared.draft.language,
                order=command.order,
                created_by=command.created_by,
                parent_id=command.parent_id,
            )
        )
        assert category.id is not None
        draft = SaveContentDraft(self._repository, self._reference_gateway).execute(
            SaveDraftCommand(
                bot_instance_id=command.bot_instance_id,
                category_id=category.id,
                expected_revision=0,
                title=shared.draft.title,
                subtitle=shared.draft.subtitle,
                language=shared.draft.language,
                blocks=resolved.blocks,
                is_shared=False,
                updated_by=command.created_by,
            )
        )
        return SharedContentImportResult(
            category=category,
            draft=draft,
            form_dependencies=resolved.form_dependencies,
        )


class GetPublishedContent:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, slug: str) -> PublishedContent:
        content = self._repository.get_published_by_slug(bot_instance_id, slug)
        if content is not None:
            return content
        category = self._repository.get_category_by_slug(bot_instance_id, slug)
        if category is not None and category.is_shortcut:
            assert category.capability_key is not None and category.capability_view_key is not None
            raise ContentIsCapabilityShortcut(category.capability_key, category.capability_view_key)
        raise ContentNotFound(slug)


class GetContentDraft:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, category_id: int) -> ContentDraft:
        draft = self._repository.get_draft(bot_instance_id, category_id)
        if draft is None:
            raise ContentNotFound(str(category_id))
        return draft


class UpdateContentCategory:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateCategoryCommand) -> ContentCategory:
        current = self._repository.get_category(command.bot_instance_id, command.category_id)
        if current is None:
            raise ContentNotFound(str(command.category_id))
        if command.change_parent:
            _validate_parent(
                self._repository,
                bot_instance_id=command.bot_instance_id,
                category_id=command.category_id,
                parent_id=command.parent_id,
            )
        changes = {
            key: value
            for key, value in {
                "icon": command.icon.strip() if command.icon else None,
                "order": command.order,
                "is_active": command.is_active,
            }.items()
            if value is not None
        }
        if command.change_parent:
            changes["parent_id"] = command.parent_id
        if command.title is not None:
            if not current.is_shortcut:
                raise ValueError("Only a capability shortcut has an editable title")
            title = command.title.strip()
            if not title:
                raise ValueError("Category title cannot be empty")
            changes["title"] = title
        if command.change_subtitle:
            if not current.is_shortcut:
                raise ValueError("Only a capability shortcut has an editable subtitle")
            changes["subtitle"] = command.subtitle.strip() if command.subtitle else None
        if command.change_image:
            if not current.is_shortcut:
                raise ValueError("Only a capability shortcut has an editable image")
            changes["image_url"] = command.image_url
        return self._repository.update_category(replace(current, **changes))


class ListContentAttachments:
    def __init__(self, catalog: ContentAssetCatalog) -> None:
        self._catalog = catalog

    def execute(
        self,
        bot_instance_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        mime_family: str | None = None,
        search: str | None = None,
    ) -> ContentAttachmentPage:
        return self._catalog.list_admin_attachments(
            bot_instance_id,
            limit=limit,
            offset=offset,
            mime_family=mime_family,
            search=search,
        )


class DeleteContentAttachment:
    def __init__(self, catalog: ContentAssetCatalog) -> None:
        self._catalog = catalog

    def execute(self, bot_instance_id: int, attachment_id: int) -> DeletedAttachment:
        return self._catalog.delete_admin_attachment(bot_instance_id, attachment_id)


class ListContentForms:
    def __init__(self, catalog: ContentAssetCatalog) -> None:
        self._catalog = catalog

    def execute(self, bot_instance_id: int) -> list[ContentFormOption]:
        return self._catalog.list_published_forms(bot_instance_id)


class ListContentTests:
    def __init__(self, catalog: ContentAssetCatalog) -> None:
        self._catalog = catalog

    def execute(self, bot_instance_id: int) -> list[ContentTestOption]:
        return self._catalog.list_published_tests(bot_instance_id)


class SaveContentDraft:
    def __init__(
        self,
        repository: ContentRepository,
        reference_gateway: ContentReferenceGateway,
    ) -> None:
        self._repository = repository
        self._reference_gateway = reference_gateway

    def execute(self, command: SaveDraftCommand) -> ContentDraft:
        title = command.title.strip()
        if not title:
            raise ValueError("Draft title cannot be empty")
        if self._repository.get_category(command.bot_instance_id, command.category_id) is None:
            raise ContentNotFound(str(command.category_id))
        normalized = validate_blocks(command.blocks)
        _, attachment_ids = extract_references(normalized)
        if command.is_shared and attachment_ids:
            raise SharedContentContainsFiles
        _validate_references(
            self._reference_gateway,
            bot_instance_id=command.bot_instance_id,
            blocks=normalized,
        )
        _validate_category_references(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            blocks=normalized,
        )
        return self._repository.save_draft(
            command.bot_instance_id,
            ContentDraft(
                category_id=command.category_id,
                title=title,
                subtitle=command.subtitle.strip() if command.subtitle else None,
                language=command.language,
                blocks=normalized,
                revision=command.expected_revision,
                is_shared=command.is_shared,
                is_filled=command.is_filled,
                image_url=command.image_url,
                header_visible=command.header_visible,
            ),
            expected_revision=command.expected_revision,
            updated_by=command.updated_by,
        )


class PublishContent:
    def __init__(
        self,
        repository: ContentRepository,
        reference_gateway: ContentReferenceGateway,
    ) -> None:
        self._repository = repository
        self._reference_gateway = reference_gateway

    def execute(self, command: PublishContentCommand) -> PublishedContent:
        draft = self._repository.get_draft(command.bot_instance_id, command.category_id)
        category = self._repository.get_category(command.bot_instance_id, command.category_id)
        if draft is None or category is None:
            raise ContentNotFound(str(command.category_id))
        if draft.revision != command.expected_revision:
            raise DraftRevisionConflict
        if category.last_published_revision >= draft.revision:
            raise NothingToPublish
        normalized = validate_blocks(draft.blocks)
        _validate_references(
            self._reference_gateway,
            bot_instance_id=command.bot_instance_id,
            blocks=normalized,
        )
        _validate_category_references(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            blocks=normalized,
        )
        _validate_publishable_references(
            self._reference_gateway,
            bot_instance_id=command.bot_instance_id,
            blocks=normalized,
        )
        return self._repository.publish(
            command.bot_instance_id,
            command.category_id,
            expected_revision=command.expected_revision,
            published_by=command.published_by,
        )


class ReorderContentCategories:
    def __init__(self, repository: ContentRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, category_ids: list[int]) -> list[ContentCategory]:
        if len(category_ids) != len(set(category_ids)):
            raise ValueError("Category order contains duplicates")
        return self._repository.reorder(bot_instance_id, category_ids)


class RecordContentCategoryOpen:
    def __init__(
        self,
        repository: ContentRepository,
        analytics_gateway: ContentAnalyticsGateway,
    ) -> None:
        self._repository = repository
        self._analytics_gateway = analytics_gateway

    def execute(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
    ) -> None:
        content = self._repository.get_published_by_category(bot_instance_id, category_id)
        if content is None:
            raise ContentNotFound(str(category_id))
        if content.version.id != version_id:
            raise PublishedVersionMismatch
        self._analytics_gateway.record_category_open(
            bot_instance_id=bot_instance_id,
            user_id=user_id,
            category_id=category_id,
            version_id=version_id,
        )


class RecordContentTabOpen:
    def __init__(
        self,
        repository: ContentRepository,
        analytics_gateway: ContentAnalyticsGateway,
    ) -> None:
        self._repository = repository
        self._analytics_gateway = analytics_gateway

    def execute(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
        tab_key: str,
    ) -> None:
        content = self._repository.get_published_by_category(bot_instance_id, category_id)
        if content is None:
            raise ContentNotFound(str(category_id))
        if content.version.id != version_id:
            raise PublishedVersionMismatch
        existing_keys = {
            tab["key"]
            for block in content.version.blocks
            if block.get("type") == "tabs"
            for tab in block["tabs"]
        }
        if tab_key not in existing_keys:
            raise ContentTabNotFound(tab_key)
        self._analytics_gateway.record_tab_open(
            bot_instance_id=bot_instance_id,
            user_id=user_id,
            category_id=category_id,
            version_id=version_id,
            tab_key=tab_key,
        )
