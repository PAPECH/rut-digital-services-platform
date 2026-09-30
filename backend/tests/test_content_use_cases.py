from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.modules.content.application.commands import (
    CreateCategoryCommand,
    ImportSharedContentDraftCommand,
    PublishContentCommand,
    SaveDraftCommand,
    UpdateCategoryCommand,
)
from app.modules.content.application.dependencies import (
    ContentDependencyResolutionResult,
    SharedContentDependencyReport,
)
from app.modules.content.application.use_cases import (
    ContentDependenciesNotReady,
    ContentIsCapabilityShortcut,
    ContentNotFound,
    CreateContentCategory,
    CrossTenantReference,
    DraftRevisionConflict,
    GetOrCreateHomeCategory,
    GetPublishedContent,
    ImportSharedContentDraft,
    InvalidCategoryParent,
    InvalidInlineImageAttachment,
    PublishContent,
    SaveContentDraft,
    ShortcutCannotHaveChildren,
    ShortcutPointerIncomplete,
    UpdateContentCategory,
)
from app.modules.content.domain.entities import (
    ContentCategory,
    ContentDraft,
    ContentVersion,
    PublishedContent,
    SharedContentDraft,
)


class InMemoryContentRepository:
    def __init__(self) -> None:
        self.categories: dict[int, ContentCategory] = {}
        self.drafts: dict[int, ContentDraft] = {}
        self.versions: dict[int, list[ContentVersion]] = {}

    def list_categories(self, bot_instance_id: int):
        return [
            (category, self.drafts.get(category_id))
            for category_id, category in self.categories.items()
            if category.bot_instance_id == bot_instance_id
        ]

    def list_published(self, bot_instance_id: int):
        result = []
        for category in self.categories.values():
            if category.bot_instance_id != bot_instance_id or category.is_home:
                continue
            content = self.get_published_by_category(bot_instance_id, category.id)
            if content is not None:
                result.append(content)
            elif category.is_shortcut:
                result.append(PublishedContent(category=category, version=None))
        return result

    def list_shared_drafts(self):
        return [
            SharedContentDraft(
                category.bot_instance_id,
                f"Бот {category.bot_instance_id}",
                category,
                self.drafts[category_id],
            )
            for category_id, category in self.categories.items()
            if self.drafts[category_id].is_shared
        ]

    def get_shared_draft(self, category_id: int):
        category = self.categories.get(category_id)
        draft = self.drafts.get(category_id)
        if not category or not draft or not draft.is_shared:
            return None
        return SharedContentDraft(
            category.bot_instance_id,
            f"Бот {category.bot_instance_id}",
            category,
            draft,
        )

    def get_category(self, bot_instance_id: int, category_id: int):
        category = self.categories.get(category_id)
        return category if category and category.bot_instance_id == bot_instance_id else None

    def get_category_by_slug(self, bot_instance_id: int, slug: str):
        return next(
            (
                category
                for category in self.categories.values()
                if category.bot_instance_id == bot_instance_id and category.slug == slug
            ),
            None,
        )

    def get_home_category(self, bot_instance_id: int):
        return next(
            (
                category
                for category in self.categories.values()
                if category.bot_instance_id == bot_instance_id and category.is_home
            ),
            None,
        )

    def get_published_by_slug(self, bot_instance_id: int, slug: str):
        category = self.get_category_by_slug(bot_instance_id, slug)
        return self.get_published_by_category(bot_instance_id, category.id) if category else None

    def get_published_by_category(self, bot_instance_id: int, category_id: int):
        category = self.get_category(bot_instance_id, category_id)
        if category is None or category.published_version_id is None:
            return None
        version = next(
            item for item in self.versions[category_id] if item.id == category.published_version_id
        )
        return PublishedContent(category=category, version=version)

    def get_draft(self, bot_instance_id: int, category_id: int):
        return self.drafts.get(category_id) if self.get_category(bot_instance_id, category_id) else None

    def create_category(self, category, draft, *, created_by):
        category_id = len(self.categories) + 1
        stored_category = replace(category, id=category_id)
        self.categories[category_id] = stored_category
        self.versions[category_id] = []
        if draft is None:
            return stored_category, None
        stored_draft = replace(draft, category_id=category_id)
        self.drafts[category_id] = stored_draft
        return stored_category, stored_draft

    def update_category(self, category):
        self.categories[category.id] = category
        return category

    def save_draft(
        self,
        bot_instance_id,
        draft,
        *,
        expected_revision,
        updated_by,
    ):
        current = self.get_draft(bot_instance_id, draft.category_id)
        if current is None:
            raise LookupError(draft.category_id)
        if current.revision != expected_revision:
            raise DraftRevisionConflict
        stored = replace(draft, blocks=deepcopy(draft.blocks), revision=current.revision + 1)
        self.drafts[draft.category_id] = stored
        return stored

    def publish(
        self,
        bot_instance_id,
        category_id,
        *,
        expected_revision,
        published_by,
    ):
        category = self.get_category(bot_instance_id, category_id)
        draft = self.get_draft(bot_instance_id, category_id)
        assert category is not None and draft is not None
        if draft.revision != expected_revision:
            raise DraftRevisionConflict
        version = ContentVersion(
            id=sum(len(items) for items in self.versions.values()) + 1,
            category_id=category_id,
            version=len(self.versions[category_id]) + 1,
            source_revision=draft.revision,
            title=draft.title,
            subtitle=draft.subtitle,
            language=draft.language,
            blocks=deepcopy(draft.blocks),
            published_by=published_by,
            published_at=datetime.now(tz=UTC),
            is_filled=draft.is_filled,
            image_url=draft.image_url,
            header_visible=draft.header_visible,
        )
        self.versions[category_id].append(version)
        stored_category = replace(
            category,
            published_version_id=version.id,
            last_published_revision=draft.revision,
        )
        self.categories[category_id] = stored_category
        return PublishedContent(category=stored_category, version=version)

    def reorder(self, bot_instance_id, category_ids):
        return []


class ReferenceGateway:
    def __init__(
        self,
        forms: dict[int, set[int]],
        attachments: dict[int, set[int]],
        capabilities: dict[int, set[tuple[str, str]]] | None = None,
        ready_forms: dict[int, set[int]] | None = None,
        attachment_mimes: dict[int, dict[int, str]] | None = None,
        tests: dict[int, set[int]] | None = None,
        ready_tests: dict[int, set[int]] | None = None,
    ) -> None:
        self.forms = forms
        self.attachments = attachments
        self.capabilities = capabilities or {}
        self.ready_forms = ready_forms if ready_forms is not None else forms
        self.attachment_mimes = attachment_mimes or {}
        self.tests = tests or {}
        self.ready_tests = ready_tests if ready_tests is not None else (tests or {})

    def missing_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]:
        return form_ids - self.forms.get(bot_instance_id, set())

    def unready_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]:
        return form_ids - self.ready_forms.get(bot_instance_id, set())

    def missing_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]:
        return test_ids - self.tests.get(bot_instance_id, set())

    def unready_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]:
        return test_ids - self.ready_tests.get(bot_instance_id, set())

    def missing_attachment_ids(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> set[int]:
        return attachment_ids - self.attachments.get(bot_instance_id, set())

    def attachment_mime_types(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> dict[int, str]:
        mimes = self.attachment_mimes.get(bot_instance_id, {})
        return {aid: mimes[aid] for aid in attachment_ids if aid in mimes}

    def missing_capability_views(
        self,
        bot_instance_id: int,
        references: set[tuple[str, str]],
    ) -> set[tuple[str, str]]:
        return references - self.capabilities.get(bot_instance_id, set())


class TemplateReferenceGateway:
    def inspect(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
    ) -> SharedContentDependencyReport:
        assert source_bot_instance_id != target_bot_instance_id
        return SharedContentDependencyReport()

    def resolve(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
        form_resolutions=(),
        created_by=None,
    ) -> ContentDependencyResolutionResult:
        assert source_bot_instance_id != target_bot_instance_id
        assert not form_resolutions
        return ContentDependencyResolutionResult(blocks=deepcopy(blocks))


def _create_category(repository: InMemoryContentRepository) -> tuple[ContentCategory, ContentDraft]:
    return CreateContentCategory(repository, ReferenceGateway(forms={}, attachments={})).execute(
        CreateCategoryCommand(
            bot_instance_id=1,
            slug="documents",
            icon="folder",
            title="Документы",
            subtitle=None,
            language="ru",
            order=0,
            created_by=5,
        )
    )


def test_draft_conflict_does_not_overwrite_newer_content() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    references = ReferenceGateway(forms={}, attachments={})
    use_case = SaveContentDraft(repository, references)
    command = SaveDraftCommand(
        bot_instance_id=1,
        category_id=category.id,
        expected_revision=0,
        title="Документы",
        subtitle=None,
        language="ru",
        blocks=[{"id": "text", "type": "paragraph", "text": "Первая версия"}],
        updated_by=5,
    )

    saved = use_case.execute(command)
    assert saved.revision == 1
    with pytest.raises(DraftRevisionConflict):
        use_case.execute(replace(command, blocks=[], title="Устаревшая запись"))
    assert repository.drafts[category.id].title == "Документы"


def test_cross_tenant_form_and_attachment_references_are_denied_on_save() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(forms={2: {9}}, attachments={2: {12}})

    with pytest.raises(CrossTenantReference) as error:
        SaveContentDraft(repository, gateway).execute(
            SaveDraftCommand(
                bot_instance_id=1,
                category_id=category.id,
                expected_revision=0,
                title="Документы",
                subtitle=None,
                language="ru",
                blocks=[
                    {"id": "form", "type": "form_action", "form_id": 9, "title": "Форма"},
                    {
                        "id": "files",
                        "type": "file_list",
                        "items": [{"attachment_id": 12, "title": "Файл"}],
                    },
                ],
                updated_by=5,
            )
        )

    assert error.value.form_ids == {9}
    assert error.value.attachment_ids == {12}
    assert repository.drafts[category.id].revision == 0


def test_cross_tenant_test_reference_is_denied_on_save() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(forms={}, attachments={}, tests={2: {9}})

    with pytest.raises(CrossTenantReference) as error:
        SaveContentDraft(repository, gateway).execute(
            SaveDraftCommand(
                bot_instance_id=1,
                category_id=category.id,
                expected_revision=0,
                title="Тесты",
                subtitle=None,
                language="ru",
                blocks=[{"id": "test", "type": "test_action", "test_id": 9, "title": "Тест"}],
                updated_by=5,
            )
        )

    assert error.value.test_ids == {9}
    assert repository.drafts[category.id].revision == 0


def test_inline_image_display_mode_is_rejected_for_a_non_image_attachment() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(
        forms={},
        attachments={1: {12}},
        attachment_mimes={1: {12: "application/pdf"}},
    )

    with pytest.raises(InvalidInlineImageAttachment) as error:
        SaveContentDraft(repository, gateway).execute(
            SaveDraftCommand(
                bot_instance_id=1,
                category_id=category.id,
                expected_revision=0,
                title="Документы",
                subtitle=None,
                language="ru",
                blocks=[
                    {
                        "id": "files",
                        "type": "file_list",
                        "items": [
                            {
                                "attachment_id": 12,
                                "title": "Инструкция",
                                "display_mode": "inline_image",
                            }
                        ],
                    }
                ],
                updated_by=5,
            )
        )

    assert error.value.attachment_ids == {12}
    assert repository.drafts[category.id].revision == 0


def test_inline_image_display_mode_is_accepted_for_an_image_attachment() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(
        forms={},
        attachments={1: {12}},
        attachment_mimes={1: {12: "image/png"}},
    )

    saved = SaveContentDraft(repository, gateway).execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=0,
            title="Документы",
            subtitle=None,
            language="ru",
            blocks=[
                {
                    "id": "files",
                    "type": "file_list",
                    "items": [
                        {
                            "attachment_id": 12,
                            "title": "Фото",
                            "display_mode": "inline_image",
                        }
                    ],
                }
            ],
            updated_by=5,
        )
    )

    assert saved.blocks[0]["items"][0]["display_mode"] == "inline_image"


def test_cross_tenant_category_parent_is_denied() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={})
    foreign_parent, _ = CreateContentCategory(repository, gateway).execute(
        CreateCategoryCommand(
            bot_instance_id=2,
            slug="foreign-parent",
            icon="folder",
            title="Чужой раздел",
            subtitle=None,
            language="ru",
            order=0,
            created_by=8,
        )
    )
    assert foreign_parent.id is not None

    with pytest.raises(InvalidCategoryParent):
        CreateContentCategory(repository, gateway).execute(
            CreateCategoryCommand(
                bot_instance_id=1,
                slug="child",
                icon="document",
                title="Вложенный раздел",
                subtitle=None,
                language="ru",
                order=0,
                created_by=5,
                parent_id=foreign_parent.id,
            )
        )


def test_existing_category_can_be_reparented_but_not_below_its_descendant() -> None:
    repository = InMemoryContentRepository()
    root, _ = _create_category(repository)
    assert root.id is not None
    child, _ = CreateContentCategory(repository, ReferenceGateway(forms={}, attachments={})).execute(
        CreateCategoryCommand(
            bot_instance_id=1,
            slug="child-category",
            icon="folder",
            title="Дочерняя категория",
            subtitle=None,
            language="ru",
            order=0,
            created_by=5,
            parent_id=root.id,
        )
    )
    assert child.id is not None

    moved = UpdateContentCategory(repository).execute(
        UpdateCategoryCommand(
            bot_instance_id=1,
            category_id=child.id,
            parent_id=None,
            change_parent=True,
        )
    )
    assert moved.parent_id is None

    UpdateContentCategory(repository).execute(
        UpdateCategoryCommand(
            bot_instance_id=1,
            category_id=child.id,
            parent_id=root.id,
            change_parent=True,
        )
    )
    with pytest.raises(InvalidCategoryParent):
        UpdateContentCategory(repository).execute(
            UpdateCategoryCommand(
                bot_instance_id=1,
                category_id=root.id,
                parent_id=child.id,
                change_parent=True,
            )
        )


def test_only_explicitly_shared_content_draft_can_be_copied_to_another_tenant() -> None:
    repository = InMemoryContentRepository()
    source, _ = _create_category(repository)
    assert source.id is not None
    source_draft = SaveContentDraft(
        repository,
        ReferenceGateway(forms={}, attachments={}),
    ).execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=source.id,
            expected_revision=0,
            title="Общая категория",
            subtitle=None,
            language="ru",
            blocks=[{"id": "text", "type": "paragraph", "text": "Шаблон"}],
            updated_by=5,
            is_shared=True,
        )
    )
    imported = ImportSharedContentDraft(
        repository,
        ReferenceGateway(forms={}, attachments={}),
        TemplateReferenceGateway(),
    ).execute(
        ImportSharedContentDraftCommand(
            bot_instance_id=2,
            source_category_id=source.id,
            slug="copied-category",
            parent_id=None,
            order=0,
            created_by=8,
        )
    )

    assert imported.category.bot_instance_id == 2
    assert imported.draft.blocks == source_draft.blocks
    assert imported.draft.blocks is not source_draft.blocks
    assert imported.draft.is_shared is False

    repository.drafts[source.id] = replace(source_draft, is_shared=False)
    with pytest.raises(ContentNotFound):
        ImportSharedContentDraft(
            repository,
            ReferenceGateway(forms={}, attachments={}),
            TemplateReferenceGateway(),
        ).execute(
            ImportSharedContentDraftCommand(
                bot_instance_id=2,
                source_category_id=source.id,
                slug="forbidden-copy",
                parent_id=None,
                order=1,
                created_by=8,
            )
        )


def test_publication_versions_are_monotonic_and_immutable() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    references = ReferenceGateway(forms={}, attachments={})
    save = SaveContentDraft(repository, references)
    publish = PublishContent(repository, references)

    first_draft = save.execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=0,
            title="Документы",
            subtitle=None,
            language="ru",
            blocks=[{"id": "text", "type": "paragraph", "text": "Первая версия"}],
            updated_by=5,
        )
    )
    first = publish.execute(PublishContentCommand(1, category.id, first_draft.revision, published_by=5))
    second_draft = save.execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=first_draft.revision,
            title="Документы",
            subtitle=None,
            language="ru",
            blocks=[{"id": "text", "type": "paragraph", "text": "Вторая версия"}],
            updated_by=5,
        )
    )
    second = publish.execute(PublishContentCommand(1, category.id, second_draft.revision, published_by=5))

    assert (first.version.version, second.version.version) == (1, 2)
    assert first.version.blocks[0]["text"] == "Первая версия"
    assert second.version.blocks[0]["text"] == "Вторая версия"
    assert len(repository.versions[category.id]) == 2


def test_content_with_unpublished_form_cannot_be_published() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(forms={1: {9}}, attachments={}, ready_forms={1: set()})
    draft = SaveContentDraft(repository, gateway).execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=0,
            title="Документы",
            subtitle=None,
            language="ru",
            blocks=[
                {"id": "request", "type": "form_action", "form_id": 9, "title": "Заявка"}
            ],
            updated_by=5,
        )
    )

    with pytest.raises(ContentDependenciesNotReady) as error:
        PublishContent(repository, gateway).execute(
            PublishContentCommand(1, category.id, draft.revision, published_by=5)
        )

    assert error.value.form_ids == {9}
    assert repository.categories[category.id].published_version_id is None


def test_content_with_unready_test_cannot_be_published() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(forms={}, attachments={}, tests={1: {9}}, ready_tests={1: set()})
    draft = SaveContentDraft(repository, gateway).execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=0,
            title="Тесты",
            subtitle=None,
            language="ru",
            blocks=[{"id": "test", "type": "test_action", "test_id": 9, "title": "Тест"}],
            updated_by=5,
        )
    )

    with pytest.raises(ContentDependenciesNotReady) as error:
        PublishContent(repository, gateway).execute(
            PublishContentCommand(1, category.id, draft.revision, published_by=5)
        )

    assert error.value.test_ids == {9}
    assert repository.categories[category.id].published_version_id is None


def test_disabled_or_cross_tenant_capability_view_is_denied() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    gateway = ReferenceGateway(
        forms={},
        attachments={},
        capabilities={2: {("request_status", "lookup")}},
    )
    with pytest.raises(CrossTenantReference) as error:
        SaveContentDraft(repository, gateway).execute(
            SaveDraftCommand(
                bot_instance_id=1,
                category_id=category.id,
                expected_revision=0,
                title="Статус",
                subtitle=None,
                language="ru",
                blocks=[
                    {
                        "id": "status",
                        "type": "capability_action",
                        "capability_key": "request_status",
                        "view_key": "lookup",
                        "title": "Проверить статус",
                    }
                ],
                updated_by=5,
            )
        )
    assert error.value.capability_views == {("request_status", "lookup")}


def test_home_category_is_created_lazily_and_published_immediately() -> None:
    repository = InMemoryContentRepository()

    category, draft = GetOrCreateHomeCategory(repository).execute(1, "Кадровые сервисы")

    assert category.is_home is True
    assert category.bot_instance_id == 1
    assert category.published_version_id is not None
    assert category.last_published_revision == draft.revision == 1
    assert draft.blocks == [
        {"id": "category_grid_default", "type": "category_grid", "parent_id": None}
    ]
    # The seed title is a template, not literal text -- frontend-miniapp resolves
    # `{{ profile.first_name }}` against the visitor's own profile, so a fresh bot's home
    # screen greets each user by name exactly like the pre-CMS hardcoded greeting did.
    assert draft.title == "Здравствуйте, {{ profile.first_name }}!"
    published = repository.get_published_by_category(1, category.id)
    assert published is not None
    assert published.version.blocks == draft.blocks
    assert published.version.header_visible is True


def test_home_category_creation_is_idempotent() -> None:
    repository = InMemoryContentRepository()

    first_category, _ = GetOrCreateHomeCategory(repository).execute(1, "Бот")
    second_category, _ = GetOrCreateHomeCategory(repository).execute(1, "Бот")

    assert first_category.id == second_category.id
    assert len([c for c in repository.categories.values() if c.is_home]) == 1


def test_home_category_is_scoped_per_bot() -> None:
    repository = InMemoryContentRepository()

    bot_1_home, _ = GetOrCreateHomeCategory(repository).execute(1, "Бот 1")
    bot_2_home, _ = GetOrCreateHomeCategory(repository).execute(2, "Бот 2")

    assert bot_1_home.id != bot_2_home.id
    assert repository.get_home_category(1).id == bot_1_home.id
    assert repository.get_home_category(2).id == bot_2_home.id


def test_saving_a_category_grid_block_with_cross_tenant_parent_is_denied() -> None:
    repository = InMemoryContentRepository()
    category, _ = _create_category(repository)
    assert category.id is not None
    other_bot_category = CreateContentCategory(repository, ReferenceGateway(forms={}, attachments={})).execute(
        CreateCategoryCommand(
            bot_instance_id=2,
            slug="other-bot-category",
            icon="folder",
            title="Чужая категория",
            subtitle=None,
            language="ru",
            order=0,
            created_by=5,
        )
    )[0]
    assert other_bot_category.id is not None
    use_case = SaveContentDraft(repository, ReferenceGateway(forms={}, attachments={}))

    with pytest.raises(CrossTenantReference) as error:
        use_case.execute(
            SaveDraftCommand(
                bot_instance_id=1,
                category_id=category.id,
                expected_revision=0,
                title="Главная",
                subtitle=None,
                language="ru",
                blocks=[
                    {
                        "id": "grid",
                        "type": "category_grid",
                        "parent_id": other_bot_category.id,
                    }
                ],
                updated_by=5,
            )
        )
    assert error.value.category_ids == {other_bot_category.id}


def test_home_category_never_appears_in_the_public_catalog() -> None:
    """The home singleton is reachable only via get_published_by_category (the dedicated
    /categories/home route) -- it must never show up as a regular navigable catalog card."""
    repository = InMemoryContentRepository()
    _create_category(repository)
    GetOrCreateHomeCategory(repository).execute(1, "Бот")

    published = repository.list_published(1)

    assert all(not content.category.is_home for content in published)


def _shortcut_command(**overrides) -> CreateCategoryCommand:
    defaults = dict(
        bot_instance_id=1,
        slug="schedule-shortcut",
        icon="calendar",
        title="Расписание",
        subtitle="Моя группа",
        language="ru",
        order=0,
        created_by=5,
        capability_key="rut_schedule",
        capability_view_key="browse",
    )
    defaults.update(overrides)
    return CreateCategoryCommand(**defaults)


def test_shortcut_requires_both_capability_key_and_view_key() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    with pytest.raises(ShortcutPointerIncomplete):
        CreateContentCategory(repository, gateway).execute(
            _shortcut_command(capability_view_key=None)
        )
    with pytest.raises(ShortcutPointerIncomplete):
        CreateContentCategory(repository, gateway).execute(_shortcut_command(capability_key=None))


def test_shortcut_capability_key_and_view_key_format_is_validated() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    with pytest.raises(ValueError):
        CreateContentCategory(repository, gateway).execute(
            _shortcut_command(capability_key="Rut-Schedule")
        )
    with pytest.raises(ValueError):
        CreateContentCategory(repository, gateway).execute(
            _shortcut_command(capability_view_key="Browse View")
        )


def test_shortcut_referencing_uninstalled_or_cross_tenant_capability_is_denied() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={2: {("rut_schedule", "browse")}})
    with pytest.raises(CrossTenantReference) as error:
        CreateContentCategory(repository, gateway).execute(_shortcut_command())
    assert error.value.capability_views == {("rut_schedule", "browse")}


def test_shortcut_is_created_without_a_draft_and_carries_its_own_card_fields() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})

    category, draft = CreateContentCategory(repository, gateway).execute(_shortcut_command())

    assert draft is None
    assert category.is_shortcut is True
    assert category.capability_key == "rut_schedule"
    assert category.capability_view_key == "browse"
    assert category.title == "Расписание"
    assert category.subtitle == "Моя группа"
    assert repository.drafts.get(category.id) is None


def test_shortcut_cannot_have_children() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    shortcut, _ = CreateContentCategory(repository, gateway).execute(_shortcut_command())
    assert shortcut.id is not None

    with pytest.raises(ShortcutCannotHaveChildren):
        CreateContentCategory(repository, gateway).execute(
            CreateCategoryCommand(
                bot_instance_id=1,
                slug="under-shortcut",
                icon="folder",
                title="Под шорткатом",
                subtitle=None,
                language="ru",
                order=0,
                created_by=5,
                parent_id=shortcut.id,
            )
        )


def test_shortcut_appears_in_the_published_catalog_interleaved_with_categories() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    category, _ = _create_category(repository)
    save = SaveContentDraft(repository, gateway)
    publish = PublishContent(repository, gateway)
    draft = save.execute(
        SaveDraftCommand(
            bot_instance_id=1,
            category_id=category.id,
            expected_revision=0,
            title="Документы",
            subtitle=None,
            language="ru",
            blocks=[],
            updated_by=5,
        )
    )
    publish.execute(PublishContentCommand(1, category.id, draft.revision, published_by=5))
    shortcut, _ = CreateContentCategory(repository, gateway).execute(_shortcut_command(order=1))

    published = repository.list_published(1)

    assert {content.category.id for content in published} == {category.id, shortcut.id}
    shortcut_content = next(c for c in published if c.category.id == shortcut.id)
    assert shortcut_content.version is None


def test_direct_navigation_to_a_shortcut_slug_reports_a_stable_failure() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    shortcut, _ = CreateContentCategory(repository, gateway).execute(_shortcut_command())

    with pytest.raises(ContentIsCapabilityShortcut) as error:
        GetPublishedContent(repository).execute(1, shortcut.slug)

    assert error.value.capability_key == "rut_schedule"
    assert error.value.view_key == "browse"


def test_shortcut_card_fields_are_editable_only_on_an_existing_shortcut() -> None:
    repository = InMemoryContentRepository()
    gateway = ReferenceGateway(forms={}, attachments={}, capabilities={1: {("rut_schedule", "browse")}})
    ordinary, _ = _create_category(repository)
    shortcut, _ = CreateContentCategory(repository, gateway).execute(_shortcut_command())

    with pytest.raises(ValueError):
        UpdateContentCategory(repository).execute(
            UpdateCategoryCommand(bot_instance_id=1, category_id=ordinary.id, title="Новый заголовок")
        )

    updated = UpdateContentCategory(repository).execute(
        UpdateCategoryCommand(
            bot_instance_id=1,
            category_id=shortcut.id,
            title="Новое расписание",
            subtitle=None,
            change_subtitle=True,
        )
    )
    assert updated.title == "Новое расписание"
    assert updated.subtitle is None
