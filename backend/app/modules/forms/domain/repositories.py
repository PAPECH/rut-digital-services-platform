from __future__ import annotations

from typing import Protocol

from .entities import FormDefinition, FormDraft, PublishedForm, SharedFormDraft


class FormRepository(Protocol):
    def list_forms(self, bot_instance_id: int) -> list[tuple[FormDefinition, FormDraft]]: ...

    def list_published(self, bot_instance_id: int) -> list[PublishedForm]: ...

    def list_shared_drafts(self) -> list[SharedFormDraft]: ...

    def get_shared_draft(self, form_id: int) -> SharedFormDraft | None: ...

    def get_form(self, bot_instance_id: int, form_id: int) -> FormDefinition | None: ...

    def get_form_by_slug(self, bot_instance_id: int, slug: str) -> FormDefinition | None: ...

    def get_draft(self, bot_instance_id: int, form_id: int) -> FormDraft | None: ...

    def get_published(self, bot_instance_id: int, form_id: int) -> PublishedForm | None: ...

    def get_version(self, bot_instance_id: int, form_id: int, version_id: int) -> PublishedForm | None: ...

    def create_form(
        self,
        definition: FormDefinition,
        draft: FormDraft,
        *,
        created_by: int | None,
    ) -> tuple[FormDefinition, FormDraft]: ...

    def update_form(self, definition: FormDefinition) -> FormDefinition: ...

    def save_draft(
        self,
        bot_instance_id: int,
        draft: FormDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> FormDraft: ...

    def publish(
        self,
        bot_instance_id: int,
        form_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedForm: ...

    def reorder(self, bot_instance_id: int, form_ids: list[int]) -> list[FormDefinition]: ...
