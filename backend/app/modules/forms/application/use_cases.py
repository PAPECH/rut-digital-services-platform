from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from ..domain.entities import FormDefinition, FormDraft, PublishedForm
from ..domain.fields import (
    FormValueValidationError,
    extract_attachment_ids,
    validate_form_fields,
    validate_submission_values,
)
from ..domain.repositories import FormRepository
from .commands import (
    CreateFormCommand,
    ImportSharedFormDraftCommand,
    PublishFormCommand,
    SaveFormDraftCommand,
    UpdateFormCommand,
)
from .ports import FormAttachmentGateway

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
HTML_TAG_RE = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")


def _plain_optional(value: str | None, *, label: str, max_length: int) -> str | None:
    normalized = value.strip() if value else None
    if normalized and len(normalized) > max_length:
        raise ValueError(f"{label} is too long")
    if normalized and HTML_TAG_RE.search(normalized):
        raise ValueError(f"HTML markup is not allowed in {label.lower()}")
    return normalized


class FormNotFound(RuntimeError):
    pass


class FormSlugExists(RuntimeError):
    pass


class FormDraftRevisionConflict(RuntimeError):
    pass


class NothingToPublish(RuntimeError):
    pass


class FormNotAvailable(RuntimeError):
    pass


class FormVersionMismatch(RuntimeError):
    pass


class FormAttachmentRejected(RuntimeError):
    def __init__(self, attachment_ids: set[int], *, reason: str) -> None:
        super().__init__(reason)
        self.attachment_ids = attachment_ids
        self.reason = reason


class CreateForm:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateFormCommand) -> tuple[FormDefinition, FormDraft]:
        slug = command.slug.strip().lower()
        name = command.name.strip()
        if not SLUG_RE.fullmatch(slug):
            raise ValueError("Invalid form slug")
        if not name:
            raise ValueError("Form name cannot be empty")
        if len(name) > 300:
            raise ValueError("Form name is too long")
        if HTML_TAG_RE.search(name):
            raise ValueError("HTML markup is not allowed in form name")
        if self._repository.get_form_by_slug(command.bot_instance_id, slug):
            raise FormSlugExists(slug)
        definition = FormDefinition(
            id=None,
            bot_instance_id=command.bot_instance_id,
            slug=slug,
            order=command.order,
        )
        draft = FormDraft(
            form_definition_id=0,
            name=name,
            description=_plain_optional(
                command.description,
                label="Form description",
                max_length=5_000,
            ),
            reply_on_accept=_plain_optional(
                command.reply_on_accept,
                label="Reply text",
                max_length=5_000,
            ),
        )
        return self._repository.create_form(definition, draft, created_by=command.created_by)


class ListForms:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[tuple[FormDefinition, FormDraft]]:
        return self._repository.list_forms(bot_instance_id)


class ListPublishedForms:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[PublishedForm]:
        return self._repository.list_published(bot_instance_id)


class ListSharedFormDrafts:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self):
        return self._repository.list_shared_drafts()


class ImportSharedFormDraft:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, command: ImportSharedFormDraftCommand) -> tuple[FormDefinition, FormDraft]:
        shared = self._repository.get_shared_draft(command.source_form_id)
        if shared is None:
            raise FormNotFound(command.source_form_id)
        definition, _ = CreateForm(self._repository).execute(
            CreateFormCommand(
                bot_instance_id=command.bot_instance_id,
                slug=command.slug,
                name=shared.draft.name,
                description=shared.draft.description,
                reply_on_accept=shared.draft.reply_on_accept,
                order=command.order,
                created_by=command.created_by,
            )
        )
        assert definition.id is not None
        draft = SaveFormDraft(self._repository).execute(
            SaveFormDraftCommand(
                bot_instance_id=command.bot_instance_id,
                form_id=definition.id,
                expected_revision=0,
                name=shared.draft.name,
                description=shared.draft.description,
                reply_on_accept=shared.draft.reply_on_accept,
                fields=shared.draft.fields,
                is_shared=False,
                updated_by=command.created_by,
            )
        )
        return definition, draft


class GetFormDraft:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, form_id: int) -> FormDraft:
        draft = self._repository.get_draft(bot_instance_id, form_id)
        if draft is None:
            raise FormNotFound(form_id)
        return draft


class GetPublishedForm:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(
        self,
        bot_instance_id: int,
        form_id: int,
        version_id: int | None = None,
    ) -> PublishedForm:
        definition = self._repository.get_form(bot_instance_id, form_id)
        if definition is None:
            raise FormNotFound(form_id)
        published = (
            self._repository.get_version(bot_instance_id, form_id, version_id)
            if version_id is not None
            else self._repository.get_published(bot_instance_id, form_id)
        )
        if published is None:
            if version_id is not None:
                raise FormVersionMismatch(version_id)
            raise FormNotFound(form_id)
        if published.definition.is_archived or not published.definition.is_active:
            raise FormNotAvailable(form_id)
        return published


class UpdateForm:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateFormCommand) -> FormDefinition:
        definition = self._repository.get_form(command.bot_instance_id, command.form_id)
        if definition is None:
            raise FormNotFound(command.form_id)
        updated = replace(
            definition,
            order=command.order if command.order is not None else definition.order,
            is_active=(command.is_active if command.is_active is not None else definition.is_active),
            show_in_catalog=(
                command.show_in_catalog
                if command.show_in_catalog is not None
                else definition.show_in_catalog
            ),
            is_archived=(command.is_archived if command.is_archived is not None else definition.is_archived),
        )
        if updated.is_archived:
            updated = replace(updated, is_active=False)
        if updated.is_active and updated.published_version_id is None:
            raise FormNotAvailable("Cannot activate an unpublished form")
        return self._repository.update_form(updated)


class SaveFormDraft:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, command: SaveFormDraftCommand) -> FormDraft:
        if self._repository.get_form(command.bot_instance_id, command.form_id) is None:
            raise FormNotFound(command.form_id)
        name = command.name.strip()
        if not name or len(name) > 300:
            raise ValueError("Form name must contain between 1 and 300 characters")
        if HTML_TAG_RE.search(name):
            raise ValueError("HTML markup is not allowed in form name")
        description = _plain_optional(
            command.description,
            label="Form description",
            max_length=5_000,
        )
        reply = _plain_optional(
            command.reply_on_accept,
            label="Reply text",
            max_length=5_000,
        )
        draft = FormDraft(
            form_definition_id=command.form_id,
            name=name,
            description=description,
            reply_on_accept=reply,
            fields=validate_form_fields(command.fields),
            revision=command.expected_revision,
            is_shared=command.is_shared,
        )
        return self._repository.save_draft(
            command.bot_instance_id,
            draft,
            expected_revision=command.expected_revision,
            updated_by=command.updated_by,
        )


class PublishForm:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, command: PublishFormCommand) -> PublishedForm:
        definition = self._repository.get_form(command.bot_instance_id, command.form_id)
        draft = self._repository.get_draft(command.bot_instance_id, command.form_id)
        if definition is None or draft is None:
            raise FormNotFound(command.form_id)
        validate_form_fields(draft.fields)
        if not any(field["active"] for field in draft.fields):
            raise ValueError("A published form must contain at least one active field")
        return self._repository.publish(
            command.bot_instance_id,
            command.form_id,
            expected_revision=command.expected_revision,
            published_by=command.published_by,
        )


class ReorderForms:
    def __init__(self, repository: FormRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, form_ids: list[int]) -> list[FormDefinition]:
        if len(form_ids) != len(set(form_ids)):
            raise ValueError("Form order contains duplicate IDs")
        return self._repository.reorder(bot_instance_id, form_ids)


class ValidateSubmission:
    def __init__(self, attachment_gateway: FormAttachmentGateway) -> None:
        self._attachments = attachment_gateway

    def execute(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        fields: list[dict[str, Any]],
        values: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = validate_submission_values(fields, values)
        references = extract_attachment_ids(fields, normalized)
        if not references:
            return normalized
        attachments = self._attachments.get_attachments(set(references))
        missing = set(references) - set(attachments)
        if missing:
            raise FormAttachmentRejected(missing, reason="Attachment does not exist")
        for attachment_id, (field_key, field) in references.items():
            attachment = attachments[attachment_id]
            if attachment.bot_instance_id != bot_instance_id:
                raise FormAttachmentRejected({attachment_id}, reason="Attachment belongs to another bot")
            if attachment.uploaded_by_user_id != user_id:
                raise FormAttachmentRejected({attachment_id}, reason="Attachment belongs to another user")
            accepted = field["accepted_mime_types"]
            wildcard = f"{attachment.mime.split('/', 1)[0]}/*" if "/" in attachment.mime else ""
            if accepted and attachment.mime not in accepted and wildcard not in accepted:
                raise FormValueValidationError("Attachment MIME type is not allowed", field_key=field_key)
            if attachment.size_bytes > field["max_size_bytes"]:
                raise FormValueValidationError("Attachment is too large", field_key=field_key)
        return normalized
