from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....models.attachment import Attachment
from ...bot_instances.infrastructure.models import BotInstanceRecord
from ..application.ports import AttachmentDescriptor
from ..application.use_cases import FormDraftRevisionConflict, NothingToPublish
from ..domain.entities import FormDefinition, FormDraft, FormVersion, PublishedForm, SharedFormDraft
from ..domain.fields import clone_fields
from .models import FormDefinitionRecord, FormDraftRecord, FormVersionRecord


def _definition(record: FormDefinitionRecord) -> FormDefinition:
    return FormDefinition(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        slug=record.slug,
        order=record.order,
        is_active=record.is_active,
        show_in_catalog=record.show_in_catalog,
        is_archived=record.is_archived,
        published_version_id=record.published_version_id,
        last_published_revision=record.last_published_revision,
    )


def _draft(record: FormDraftRecord) -> FormDraft:
    return FormDraft(
        form_definition_id=record.form_definition_id,
        name=record.name,
        description=record.description,
        reply_on_accept=record.reply_on_accept,
        fields=clone_fields(record.fields or []),
        revision=record.revision,
        is_shared=record.is_shared,
    )


def _version(record: FormVersionRecord) -> FormVersion:
    return FormVersion(
        id=record.id,
        form_definition_id=record.form_definition_id,
        version=record.version,
        source_revision=record.source_revision,
        name=record.name,
        description=record.description,
        reply_on_accept=record.reply_on_accept,
        fields=clone_fields(record.fields or []),
        published_by=record.published_by,
        published_at=record.published_at,
    )


class SqlAlchemyFormRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_forms(self, bot_instance_id: int) -> list[tuple[FormDefinition, FormDraft]]:
        rows = self._session.execute(
            select(FormDefinitionRecord, FormDraftRecord)
            .join(
                FormDraftRecord,
                FormDraftRecord.form_definition_id == FormDefinitionRecord.id,
            )
            .where(FormDefinitionRecord.bot_instance_id == bot_instance_id)
            .order_by(FormDefinitionRecord.order, FormDefinitionRecord.id)
        ).all()
        return [(_definition(definition), _draft(draft)) for definition, draft in rows]

    def list_published(self, bot_instance_id: int) -> list[PublishedForm]:
        rows = self._session.execute(
            select(FormDefinitionRecord, FormVersionRecord)
            .join(
                FormVersionRecord,
                FormVersionRecord.id == FormDefinitionRecord.published_version_id,
            )
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.is_active.is_(True),
                FormDefinitionRecord.is_archived.is_(False),
                FormDefinitionRecord.show_in_catalog.is_(True),
            )
            .order_by(FormDefinitionRecord.order, FormDefinitionRecord.id)
        ).all()
        return [
            PublishedForm(definition=_definition(definition), version=_version(version))
            for definition, version in rows
        ]

    def list_shared_drafts(self) -> list[SharedFormDraft]:
        rows = self._session.execute(
            select(FormDefinitionRecord, FormDraftRecord, BotInstanceRecord.name)
            .join(FormDraftRecord, FormDraftRecord.form_definition_id == FormDefinitionRecord.id)
            .join(BotInstanceRecord, BotInstanceRecord.id == FormDefinitionRecord.bot_instance_id)
            .where(
                FormDraftRecord.is_shared.is_(True),
                FormDefinitionRecord.is_archived.is_(False),
            )
            .order_by(FormDraftRecord.updated_at.desc(), FormDefinitionRecord.id.desc())
        ).all()
        return [
            SharedFormDraft(
                source_bot_instance_id=definition.bot_instance_id,
                source_bot_name=bot_name,
                definition=_definition(definition),
                draft=_draft(draft),
            )
            for definition, draft, bot_name in rows
        ]

    def get_shared_draft(self, form_id: int) -> SharedFormDraft | None:
        row = self._session.execute(
            select(FormDefinitionRecord, FormDraftRecord, BotInstanceRecord.name)
            .join(FormDraftRecord, FormDraftRecord.form_definition_id == FormDefinitionRecord.id)
            .join(BotInstanceRecord, BotInstanceRecord.id == FormDefinitionRecord.bot_instance_id)
            .where(
                FormDefinitionRecord.id == form_id,
                FormDraftRecord.is_shared.is_(True),
                FormDefinitionRecord.is_archived.is_(False),
            )
        ).one_or_none()
        if row is None:
            return None
        definition, draft, bot_name = row
        return SharedFormDraft(
            source_bot_instance_id=definition.bot_instance_id,
            source_bot_name=bot_name,
            definition=_definition(definition),
            draft=_draft(draft),
        )

    def get_form(self, bot_instance_id: int, form_id: int) -> FormDefinition | None:
        record = self._session.execute(
            select(FormDefinitionRecord).where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.id == form_id,
            )
        ).scalar_one_or_none()
        return _definition(record) if record else None

    def get_form_by_slug(self, bot_instance_id: int, slug: str) -> FormDefinition | None:
        record = self._session.execute(
            select(FormDefinitionRecord).where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.slug == slug,
            )
        ).scalar_one_or_none()
        return _definition(record) if record else None

    def get_draft(self, bot_instance_id: int, form_id: int) -> FormDraft | None:
        record = self._session.execute(
            select(FormDraftRecord)
            .join(
                FormDefinitionRecord,
                FormDefinitionRecord.id == FormDraftRecord.form_definition_id,
            )
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDraftRecord.form_definition_id == form_id,
            )
        ).scalar_one_or_none()
        return _draft(record) if record else None

    def get_published(self, bot_instance_id: int, form_id: int) -> PublishedForm | None:
        row = self._session.execute(
            select(FormDefinitionRecord, FormVersionRecord)
            .join(
                FormVersionRecord,
                FormVersionRecord.id == FormDefinitionRecord.published_version_id,
            )
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.id == form_id,
            )
        ).one_or_none()
        if row is None:
            return None
        definition, version = row
        return PublishedForm(definition=_definition(definition), version=_version(version))

    def get_version(
        self,
        bot_instance_id: int,
        form_id: int,
        version_id: int,
    ) -> PublishedForm | None:
        row = self._session.execute(
            select(FormDefinitionRecord, FormVersionRecord)
            .join(
                FormVersionRecord,
                FormVersionRecord.form_definition_id == FormDefinitionRecord.id,
            )
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.id == form_id,
                FormVersionRecord.id == version_id,
            )
        ).one_or_none()
        if row is None:
            return None
        definition, version = row
        return PublishedForm(definition=_definition(definition), version=_version(version))

    def create_form(
        self,
        definition: FormDefinition,
        draft: FormDraft,
        *,
        created_by: int | None,
    ) -> tuple[FormDefinition, FormDraft]:
        record = FormDefinitionRecord(
            bot_instance_id=definition.bot_instance_id,
            slug=definition.slug,
            order=definition.order,
            is_active=False,
            show_in_catalog=definition.show_in_catalog,
            is_archived=False,
            last_published_revision=-1,
            name=draft.name,
            description=draft.description,
            reply_on_accept=draft.reply_on_accept,
            created_by=created_by,
        )
        self._session.add(record)
        self._session.flush()
        draft_record = FormDraftRecord(
            form_definition_id=record.id,
            name=draft.name,
            description=draft.description,
            reply_on_accept=draft.reply_on_accept,
            fields=clone_fields(draft.fields),
            revision=0,
            is_shared=draft.is_shared,
            updated_by=created_by,
        )
        self._session.add(draft_record)
        self._session.flush()
        return _definition(record), _draft(draft_record)

    def update_form(self, definition: FormDefinition) -> FormDefinition:
        record = self._session.execute(
            select(FormDefinitionRecord).where(
                FormDefinitionRecord.id == definition.id,
                FormDefinitionRecord.bot_instance_id == definition.bot_instance_id,
            )
        ).scalar_one()
        record.order = definition.order
        record.is_active = definition.is_active
        record.show_in_catalog = definition.show_in_catalog
        record.is_archived = definition.is_archived
        self._session.flush()
        return _definition(record)

    def save_draft(
        self,
        bot_instance_id: int,
        draft: FormDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> FormDraft:
        record = self._session.execute(
            select(FormDraftRecord)
            .join(
                FormDefinitionRecord,
                FormDefinitionRecord.id == FormDraftRecord.form_definition_id,
            )
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDraftRecord.form_definition_id == draft.form_definition_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(draft.form_definition_id)
        if record.revision != expected_revision:
            raise FormDraftRevisionConflict
        record.name = draft.name
        record.description = draft.description
        record.reply_on_accept = draft.reply_on_accept
        record.fields = clone_fields(draft.fields)
        record.revision += 1
        record.is_shared = draft.is_shared
        record.updated_by = updated_by

        # Keep legacy summary columns meaningful for modules not migrated in this slice.
        definition = self._session.get(FormDefinitionRecord, draft.form_definition_id)
        assert definition is not None
        definition.name = draft.name[:200]
        definition.description = draft.description
        definition.reply_on_accept = draft.reply_on_accept
        self._session.flush()
        return _draft(record)

    def publish(
        self,
        bot_instance_id: int,
        form_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedForm:
        definition = self._session.execute(
            select(FormDefinitionRecord)
            .where(
                FormDefinitionRecord.bot_instance_id == bot_instance_id,
                FormDefinitionRecord.id == form_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        draft = self._session.execute(
            select(FormDraftRecord).where(FormDraftRecord.form_definition_id == form_id).with_for_update()
        ).scalar_one_or_none()
        if definition is None or draft is None:
            raise LookupError(form_id)
        if draft.revision != expected_revision:
            raise FormDraftRevisionConflict
        if definition.last_published_revision >= draft.revision:
            raise NothingToPublish
        next_version = (
            self._session.execute(
                select(func.max(FormVersionRecord.version)).where(
                    FormVersionRecord.form_definition_id == form_id
                )
            ).scalar_one()
            or 0
        ) + 1
        version = FormVersionRecord(
            form_definition_id=form_id,
            version=next_version,
            source_revision=draft.revision,
            name=draft.name,
            description=draft.description,
            reply_on_accept=draft.reply_on_accept,
            fields=clone_fields(draft.fields or []),
            published_by=published_by,
            published_at=datetime.now(tz=UTC),
        )
        self._session.add(version)
        self._session.flush()
        definition.published_version_id = version.id
        definition.last_published_revision = draft.revision
        self._session.flush()
        return PublishedForm(definition=_definition(definition), version=_version(version))

    def reorder(self, bot_instance_id: int, form_ids: list[int]) -> list[FormDefinition]:
        records = list(
            self._session.execute(
                select(FormDefinitionRecord)
                .where(FormDefinitionRecord.bot_instance_id == bot_instance_id)
                .with_for_update()
            ).scalars()
        )
        if {record.id for record in records} != set(form_ids):
            raise ValueError("Form order must include every form in the current bot")
        by_id = {record.id: record for record in records}
        for order, form_id in enumerate(form_ids):
            by_id[form_id].order = order
        self._session.flush()
        return [_definition(by_id[form_id]) for form_id in form_ids]


class SqlAlchemyFormAttachmentGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_attachments(self, attachment_ids: set[int]) -> dict[int, AttachmentDescriptor]:
        if not attachment_ids:
            return {}
        records = self._session.execute(select(Attachment).where(Attachment.id.in_(attachment_ids))).scalars()
        return {
            record.id: AttachmentDescriptor(
                id=record.id,
                bot_instance_id=record.bot_instance_id,
                uploaded_by_user_id=record.uploaded_by_user_id,
                mime=record.mime,
                size_bytes=record.size_bytes,
            )
            for record in records
        }
