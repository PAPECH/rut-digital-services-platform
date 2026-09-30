from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.modules.forms.application.commands import (
    CreateFormCommand,
    ImportSharedFormDraftCommand,
    PublishFormCommand,
    SaveFormDraftCommand,
)
from app.modules.forms.application.use_cases import (
    CreateForm,
    FormDraftRevisionConflict,
    FormNotFound,
    FormVersionMismatch,
    GetPublishedForm,
    ImportSharedFormDraft,
    PublishForm,
    SaveFormDraft,
)
from app.modules.forms.domain.entities import (
    FormDefinition,
    FormDraft,
    FormVersion,
    PublishedForm,
    SharedFormDraft,
)


class InMemoryFormRepository:
    def __init__(self) -> None:
        self.forms: dict[int, FormDefinition] = {}
        self.drafts: dict[int, FormDraft] = {}
        self.versions: dict[int, list[FormVersion]] = {}

    def list_forms(self, bot_instance_id):
        return [
            (form, self.drafts[form_id])
            for form_id, form in self.forms.items()
            if form.bot_instance_id == bot_instance_id
        ]

    def list_published(self, bot_instance_id):
        return [
            item
            for form in self.forms.values()
            if form.bot_instance_id == bot_instance_id
            and (item := self.get_published(bot_instance_id, form.id))
        ]

    def list_shared_drafts(self):
        return [
            SharedFormDraft(form.bot_instance_id, f"Бот {form.bot_instance_id}", form, self.drafts[form_id])
            for form_id, form in self.forms.items()
            if self.drafts[form_id].is_shared and not form.is_archived
        ]

    def get_shared_draft(self, form_id):
        form = self.forms.get(form_id)
        draft = self.drafts.get(form_id)
        if not form or not draft or not draft.is_shared or form.is_archived:
            return None
        return SharedFormDraft(form.bot_instance_id, f"Бот {form.bot_instance_id}", form, draft)

    def get_form(self, bot_instance_id, form_id):
        form = self.forms.get(form_id)
        return form if form and form.bot_instance_id == bot_instance_id else None

    def get_form_by_slug(self, bot_instance_id, slug):
        return next(
            (
                form
                for form in self.forms.values()
                if form.bot_instance_id == bot_instance_id and form.slug == slug
            ),
            None,
        )

    def get_draft(self, bot_instance_id, form_id):
        return self.drafts.get(form_id) if self.get_form(bot_instance_id, form_id) else None

    def get_published(self, bot_instance_id, form_id):
        form = self.get_form(bot_instance_id, form_id)
        if not form or form.published_version_id is None:
            return None
        version = next(item for item in self.versions[form_id] if item.id == form.published_version_id)
        return PublishedForm(form, version)

    def get_version(self, bot_instance_id, form_id, version_id):
        form = self.get_form(bot_instance_id, form_id)
        version = next((item for item in self.versions.get(form_id, []) if item.id == version_id), None)
        return PublishedForm(form, version) if form and version else None

    def create_form(self, definition, draft, *, created_by):
        form_id = len(self.forms) + 1
        form = replace(definition, id=form_id)
        stored = replace(draft, form_definition_id=form_id)
        self.forms[form_id] = form
        self.drafts[form_id] = stored
        self.versions[form_id] = []
        return form, stored

    def update_form(self, definition):
        self.forms[definition.id] = definition
        return definition

    def save_draft(self, bot_instance_id, draft, *, expected_revision, updated_by):
        current = self.get_draft(bot_instance_id, draft.form_definition_id)
        if current is None:
            raise LookupError
        if current.revision != expected_revision:
            raise FormDraftRevisionConflict
        saved = replace(draft, fields=deepcopy(draft.fields), revision=current.revision + 1)
        self.drafts[draft.form_definition_id] = saved
        return saved

    def publish(self, bot_instance_id, form_id, *, expected_revision, published_by):
        form = self.get_form(bot_instance_id, form_id)
        draft = self.get_draft(bot_instance_id, form_id)
        assert form and draft
        if draft.revision != expected_revision:
            raise FormDraftRevisionConflict
        version = FormVersion(
            sum(len(items) for items in self.versions.values()) + 1,
            form_id,
            len(self.versions[form_id]) + 1,
            draft.revision,
            draft.name,
            draft.description,
            draft.reply_on_accept,
            deepcopy(draft.fields),
            published_by,
            datetime.now(tz=UTC),
        )
        self.versions[form_id].append(version)
        updated = replace(
            form, published_version_id=version.id, last_published_revision=draft.revision, is_active=True
        )
        self.forms[form_id] = updated
        return PublishedForm(updated, version)

    def reorder(self, bot_instance_id, form_ids):
        return [self.forms[form_id] for form_id in form_ids]


def checkbox(label: str):
    return {
        "key": "agreement",
        "type": "checkbox",
        "label": label,
        "help_text": None,
        "required": True,
        "active": True,
        "profile_key": None,
        "default": False,
    }


def test_published_versions_are_immutable_and_old_version_is_addressable() -> None:
    repository = InMemoryFormRepository()
    definition, _ = CreateForm(repository).execute(
        CreateFormCommand(1, "request", "Заявка", None, None, 0, 3)
    )
    assert definition.id is not None
    first_draft = SaveFormDraft(repository).execute(
        SaveFormDraftCommand(1, definition.id, 0, "Заявка", None, None, [checkbox("Согласие v1")], 3)
    )
    first = PublishForm(repository).execute(PublishFormCommand(1, definition.id, first_draft.revision, 3))
    second_draft = SaveFormDraft(repository).execute(
        SaveFormDraftCommand(
            1, definition.id, first_draft.revision, "Заявка", None, None, [checkbox("Согласие v2")], 3
        )
    )
    second = PublishForm(repository).execute(PublishFormCommand(1, definition.id, second_draft.revision, 3))
    old = GetPublishedForm(repository).execute(1, definition.id, first.version.id)

    assert (first.version.version, second.version.version) == (1, 2)
    assert old.version.fields[0]["label"] == "Согласие v1"
    assert second.version.fields[0]["label"] == "Согласие v2"


def test_form_from_another_tenant_is_not_visible() -> None:
    repository = InMemoryFormRepository()
    definition, _ = CreateForm(repository).execute(
        CreateFormCommand(1, "request", "Заявка", None, None, 0, 3)
    )
    assert definition.id is not None
    with pytest.raises(FormNotFound):
        GetPublishedForm(repository).execute(2, definition.id)


def test_only_explicitly_shared_form_draft_can_be_copied_to_another_tenant() -> None:
    repository = InMemoryFormRepository()
    source, _ = CreateForm(repository).execute(
        CreateFormCommand(1, "source-form", "Исходная форма", None, None, 0, 3)
    )
    assert source.id is not None
    source_draft = SaveFormDraft(repository).execute(
        SaveFormDraftCommand(
            1,
            source.id,
            0,
            "Исходная форма",
            None,
            None,
            [checkbox("Согласие")],
            3,
            is_shared=True,
        )
    )
    imported, imported_draft = ImportSharedFormDraft(repository).execute(
        ImportSharedFormDraftCommand(2, source.id, "copied-form", 0, 8)
    )

    assert imported.bot_instance_id == 2
    assert imported_draft.fields == source_draft.fields
    assert imported_draft.fields is not source_draft.fields
    assert imported_draft.is_shared is False

    repository.drafts[source.id] = replace(source_draft, is_shared=False)
    with pytest.raises(FormNotFound):
        ImportSharedFormDraft(repository).execute(
            ImportSharedFormDraftCommand(2, source.id, "forbidden-copy", 1, 8)
        )


def test_version_from_another_form_is_rejected_as_mismatch() -> None:
    repository = InMemoryFormRepository()
    first, _ = CreateForm(repository).execute(CreateFormCommand(1, "first", "Первая", None, None, 0, 3))
    second, _ = CreateForm(repository).execute(CreateFormCommand(1, "second", "Вторая", None, None, 1, 3))
    assert first.id is not None and second.id is not None
    draft = SaveFormDraft(repository).execute(
        SaveFormDraftCommand(1, first.id, 0, "Первая", None, None, [checkbox("Да")], 3)
    )
    published = PublishForm(repository).execute(PublishFormCommand(1, first.id, draft.revision, 3))

    with pytest.raises(FormVersionMismatch):
        GetPublishedForm(repository).execute(1, second.id, published.version.id)
