from __future__ import annotations

import pytest

from app.modules.content.application.commands import (
    CreateCategoryCommand,
    ImportSharedContentDraftCommand,
    SaveDraftCommand,
)
from app.modules.content.application.dependencies import (
    ContentDependencyCopyForbidden,
    ContentDependencyResolutionInvalid,
    FormDependencyResolution,
)
from app.modules.content.application.use_cases import (
    CreateContentCategory,
    ImportSharedContentDraft,
    SaveContentDraft,
)
from app.modules.content.infrastructure.repositories import FormContentTemplateDependencyGateway
from app.modules.forms.application.commands import (
    CreateFormCommand,
    PublishFormCommand,
    SaveFormDraftCommand,
)
from app.modules.forms.application.use_cases import CreateForm, PublishForm, SaveFormDraft
from tests.test_content_use_cases import InMemoryContentRepository, ReferenceGateway
from tests.test_form_use_cases import InMemoryFormRepository, checkbox


def _create_form(
    repository: InMemoryFormRepository,
    *,
    bot_instance_id: int,
    slug: str,
    name: str,
    shared: bool = False,
    published: bool = False,
) -> int:
    definition, _ = CreateForm(repository).execute(
        CreateFormCommand(bot_instance_id, slug, name, None, None, 0, 7)
    )
    assert definition.id is not None
    draft = SaveFormDraft(repository).execute(
        SaveFormDraftCommand(
            bot_instance_id,
            definition.id,
            0,
            name,
            None,
            None,
            [checkbox("Согласие")],
            7,
            is_shared=shared,
        )
    )
    if published:
        PublishForm(repository).execute(
            PublishFormCommand(bot_instance_id, definition.id, draft.revision, 7)
        )
    return definition.id


def _blocks(form_id: int) -> list[dict]:
    return [{"id": "request", "type": "form_action", "form_id": form_id, "title": "Заявка"}]


def test_preflight_reports_copyable_form_and_only_current_tenant_targets() -> None:
    forms = InMemoryFormRepository()
    source_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="source-request",
        name="Исходная заявка",
        shared=True,
    )
    target_id = _create_form(
        forms,
        bot_instance_id=2,
        slug="target-request",
        name="Форма второго бота",
        published=True,
    )
    _create_form(
        forms,
        bot_instance_id=3,
        slug="foreign-request",
        name="Форма чужого бота",
        published=True,
    )

    report = FormContentTemplateDependencyGateway(forms).inspect(
        source_bot_instance_id=1,
        target_bot_instance_id=2,
        blocks=_blocks(source_id),
    )

    assert report.form_dependencies[0].status == "copy_available"
    assert report.form_dependencies[0].source_is_shared is True
    assert [target.id for target in report.form_targets] == [target_id]


def test_cross_tenant_target_form_resolution_is_rejected() -> None:
    forms = InMemoryFormRepository()
    source_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="source-request",
        name="Исходная заявка",
    )
    _create_form(
        forms,
        bot_instance_id=2,
        slug="target-request",
        name="Форма второго бота",
        published=True,
    )
    foreign_id = _create_form(
        forms,
        bot_instance_id=3,
        slug="foreign-request",
        name="Форма чужого бота",
        published=True,
    )

    with pytest.raises(ContentDependencyResolutionInvalid):
        FormContentTemplateDependencyGateway(forms).resolve(
            source_bot_instance_id=1,
            target_bot_instance_id=2,
            blocks=_blocks(source_id),
            form_resolutions=(
                FormDependencyResolution(source_id, "use_existing", foreign_id),
            ),
            created_by=7,
        )


def test_shared_form_is_copied_as_unpublished_target_draft_and_reference_is_remapped() -> None:
    forms = InMemoryFormRepository()
    source_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="source-request",
        name="Исходная заявка",
        shared=True,
    )

    result = FormContentTemplateDependencyGateway(forms).resolve(
        source_bot_instance_id=1,
        target_bot_instance_id=2,
        blocks=_blocks(source_id),
        form_resolutions=(FormDependencyResolution(source_id, "copy_shared"),),
        created_by=9,
    )

    target_id = result.form_dependencies[0].target_id
    copied = forms.get_form(2, target_id)
    copied_draft = forms.get_draft(2, target_id)
    assert copied is not None and copied.slug == "source-request"
    assert copied.published_version_id is None and copied.is_active is False
    assert copied_draft is not None and copied_draft.is_shared is False
    assert result.blocks[0]["form_id"] == target_id
    assert result.form_dependencies[0].target_ready is False


def test_non_shared_form_cannot_be_copied_by_dependency_adapter() -> None:
    forms = InMemoryFormRepository()
    source_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="private-request",
        name="Закрытая заявка",
    )

    with pytest.raises(ContentDependencyResolutionInvalid):
        FormContentTemplateDependencyGateway(forms).resolve(
            source_bot_instance_id=1,
            target_bot_instance_id=2,
            blocks=_blocks(source_id),
            form_resolutions=(FormDependencyResolution(source_id, "copy_shared"),),
            created_by=9,
        )


def test_missing_resolution_auto_copies_shared_form_for_legacy_client() -> None:
    forms = InMemoryFormRepository()
    source_form_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="source-request",
        name="Исходная заявка",
        shared=True,
    )
    content = InMemoryContentRepository()
    category, _ = CreateContentCategory(content, ReferenceGateway({}, {})).execute(
        CreateCategoryCommand(1, "shared-page", "folder", "Общая", None, "ru", 0, 7)
    )
    assert category.id is not None
    SaveContentDraft(content, ReferenceGateway({1: {source_form_id}}, {})).execute(
        SaveDraftCommand(
            1,
            category.id,
            0,
            "Общая",
            None,
            "ru",
            _blocks(source_form_id),
            7,
            is_shared=True,
        )
    )

    imported = ImportSharedContentDraft(
        content,
        ReferenceGateway({2: {2}}, {}),
        FormContentTemplateDependencyGateway(forms),
    ).execute(
        ImportSharedContentDraftCommand(
            bot_instance_id=2,
            source_category_id=category.id,
            slug="copy-page",
            parent_id=None,
            order=0,
            created_by=9,
            can_copy_forms=True,
        )
    )

    assert imported.form_dependencies[0].action == "copy_shared"
    target_form_id = imported.form_dependencies[0].target_id
    assert imported.draft.blocks[0]["form_id"] == target_form_id
    assert forms.get_form(2, target_form_id) is not None


def test_content_manager_without_form_permission_cannot_copy_dependency() -> None:
    forms = InMemoryFormRepository()
    source_form_id = _create_form(
        forms,
        bot_instance_id=1,
        slug="source-request",
        name="Исходная заявка",
        shared=True,
    )
    content = InMemoryContentRepository()
    category, _ = CreateContentCategory(content, ReferenceGateway({}, {})).execute(
        CreateCategoryCommand(1, "shared-page", "folder", "Общая", None, "ru", 0, 7)
    )
    assert category.id is not None
    SaveContentDraft(content, ReferenceGateway({1: {source_form_id}}, {})).execute(
        SaveDraftCommand(
            1,
            category.id,
            0,
            "Общая",
            None,
            "ru",
            _blocks(source_form_id),
            7,
            is_shared=True,
        )
    )

    with pytest.raises(ContentDependencyCopyForbidden):
        ImportSharedContentDraft(
            content,
            ReferenceGateway({}, {}),
            FormContentTemplateDependencyGateway(forms),
        ).execute(
            ImportSharedContentDraftCommand(
                bot_instance_id=2,
                source_category_id=category.id,
                slug="copy-page",
                parent_id=None,
                order=0,
                created_by=9,
                form_resolutions=(
                    FormDependencyResolution(source_form_id, "copy_shared"),
                ),
                can_copy_forms=False,
            )
        )

    assert forms.list_forms(2) == []
    assert len(content.categories) == 1
