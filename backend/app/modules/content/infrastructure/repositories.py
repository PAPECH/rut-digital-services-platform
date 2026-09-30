from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ....models.attachment import Attachment
from ....models.form import FormTemplate, FormVersionRecord
from ....models.logger import UserAction
from ....services.files import delete_file
from ...bot_instances.infrastructure.models import BotInstanceRecord
from ...capabilities.infrastructure.catalog import capability_registry
from ...capabilities.infrastructure.models import CapabilityInstallationRecord
from ...form_tests.infrastructure.models import TestDefinitionRecord, TestVersionRecord
from ...forms.application.commands import ImportSharedFormDraftCommand
from ...forms.application.use_cases import ImportSharedFormDraft
from ...forms.domain.entities import FormDefinition
from ...forms.domain.repositories import FormRepository
from ...forms.infrastructure.repositories import SqlAlchemyFormRepository
from ..application.dependencies import (
    ContentDependencyResolutionInvalid,
    ContentDependencyResolutionResult,
    DependencyBlocker,
    FormDependency,
    FormDependencyResolution,
    FormDependencyTarget,
    ResolvedFormDependency,
    SharedContentDependencyReport,
)
from ..application.use_cases import (
    ContentAttachmentInUse,
    ContentAttachmentNotFound,
    DraftRevisionConflict,
    NothingToPublish,
    SharedContentContainsFiles,
)
from ..domain.blocks import (
    clone_blocks,
    extract_card_image_attachment_id,
    extract_references,
    remap_form_references,
)
from ..domain.entities import (
    AttachmentReference,
    ContentAttachment,
    ContentAttachmentPage,
    ContentCategory,
    ContentDraft,
    ContentFormOption,
    ContentTestOption,
    ContentVersion,
    DeletedAttachment,
    PublishedContent,
    SharedContentDraft,
)
from .models import (
    ContentAttachmentReferenceRecord,
    ContentCategoryRecord,
    ContentDraftRecord,
    ContentVersionRecord,
)


def _sync_attachment_references(
    session: Session,
    *,
    bot_instance_id: int,
    category_id: int,
    scope: str,
    blocks: list[dict],
    image_url: str | None,
) -> None:
    """Replace every `scope` row for this category with what `blocks`/`image_url` reference right
    now -- see `ContentAttachmentReferenceRecord` docstring for why this is current-state-only,
    not a history table."""
    session.execute(
        delete(ContentAttachmentReferenceRecord).where(
            ContentAttachmentReferenceRecord.category_id == category_id,
            ContentAttachmentReferenceRecord.scope == scope,
        )
    )
    _, attachment_ids = extract_references(blocks)
    now = datetime.now(tz=UTC)
    usages: set[tuple[int, str]] = {(attachment_id, "file_list_item") for attachment_id in attachment_ids}
    card_image_id = extract_card_image_attachment_id(image_url)
    if card_image_id is not None:
        usages.add((card_image_id, "card_image"))
    for attachment_id, usage in usages:
        session.add(
            ContentAttachmentReferenceRecord(
                bot_instance_id=bot_instance_id,
                attachment_id=attachment_id,
                category_id=category_id,
                scope=scope,
                usage=usage,
                created_at=now,
            )
        )
    session.flush()


def _category(record: ContentCategoryRecord) -> ContentCategory:
    return ContentCategory(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        slug=record.slug,
        icon=record.icon,
        parent_id=record.parent_id,
        order=record.order,
        is_active=record.is_active,
        published_version_id=record.published_version_id,
        last_published_revision=record.last_published_revision,
        is_home=record.is_home,
        capability_key=record.capability_key,
        capability_view_key=record.capability_view_key,
        title=record.title,
        subtitle=record.subtitle,
        image_url=record.image_url,
    )


def _draft(record: ContentDraftRecord) -> ContentDraft:
    return ContentDraft(
        category_id=record.category_id,
        title=record.title,
        subtitle=record.subtitle,
        language=record.language,
        blocks=clone_blocks(record.blocks or []),
        revision=record.revision,
        is_shared=record.is_shared,
        is_filled=record.is_filled,
        image_url=record.image_url,
        header_visible=record.header_visible,
    )


def _version(record: ContentVersionRecord) -> ContentVersion:
    return ContentVersion(
        id=record.id,
        category_id=record.category_id,
        version=record.version,
        source_revision=record.source_revision,
        title=record.title,
        subtitle=record.subtitle,
        language=record.language,
        blocks=clone_blocks(record.blocks or []),
        published_by=record.published_by,
        published_at=record.published_at,
        is_filled=record.is_filled,
        image_url=record.image_url,
        header_visible=record.header_visible,
    )


class SqlAlchemyContentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_categories(
        self, bot_instance_id: int
    ) -> list[tuple[ContentCategory, ContentDraft | None]]:
        # A capability shortcut has no draft row -- outerjoin so it still appears in the admin
        # tree (an innerjoin would silently exclude every shortcut).
        rows = self._session.execute(
            select(ContentCategoryRecord, ContentDraftRecord)
            .outerjoin(ContentDraftRecord, ContentDraftRecord.category_id == ContentCategoryRecord.id)
            .where(ContentCategoryRecord.bot_instance_id == bot_instance_id)
            .order_by(ContentCategoryRecord.order, ContentCategoryRecord.id)
        ).all()
        return [(_category(category), _draft(draft) if draft else None) for category, draft in rows]

    def list_published(self, bot_instance_id: int) -> list[PublishedContent]:
        # The home singleton is reachable only through get_published_by_category (via the
        # dedicated /categories/home route) -- it must never appear as a regular navigable card
        # in the catalog/category grid it itself is meant to host.
        # A capability shortcut has no published version -- outerjoin (rather than the innerjoin
        # a normal category's `published_version_id` would need) and admit it via the OR clause
        # below, so it still appears -- interleaved in its real sibling position -- in the same
        # single, correctly ordered query instead of a second query merged in application code.
        rows = self._session.execute(
            select(ContentCategoryRecord, ContentVersionRecord)
            .outerjoin(
                ContentVersionRecord,
                ContentVersionRecord.id == ContentCategoryRecord.published_version_id,
            )
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.is_active.is_(True),
                ContentCategoryRecord.is_home.is_(False),
                (ContentCategoryRecord.published_version_id.is_not(None))
                | (ContentCategoryRecord.capability_key.is_not(None)),
            )
            .order_by(ContentCategoryRecord.order, ContentCategoryRecord.id)
        ).all()
        return [
            PublishedContent(category=_category(category), version=_version(version) if version else None)
            for category, version in rows
        ]

    def list_shared_drafts(self) -> list[SharedContentDraft]:
        rows = self._session.execute(
            select(ContentCategoryRecord, ContentDraftRecord, BotInstanceRecord.name)
            .join(ContentDraftRecord, ContentDraftRecord.category_id == ContentCategoryRecord.id)
            .join(BotInstanceRecord, BotInstanceRecord.id == ContentCategoryRecord.bot_instance_id)
            .where(ContentDraftRecord.is_shared.is_(True))
            .order_by(ContentDraftRecord.updated_at.desc(), ContentCategoryRecord.id.desc())
        ).all()
        return [
            SharedContentDraft(
                source_bot_instance_id=category.bot_instance_id,
                source_bot_name=bot_name,
                category=_category(category),
                draft=_draft(draft),
            )
            for category, draft, bot_name in rows
        ]

    def get_shared_draft(self, category_id: int) -> SharedContentDraft | None:
        row = self._session.execute(
            select(ContentCategoryRecord, ContentDraftRecord, BotInstanceRecord.name)
            .join(ContentDraftRecord, ContentDraftRecord.category_id == ContentCategoryRecord.id)
            .join(BotInstanceRecord, BotInstanceRecord.id == ContentCategoryRecord.bot_instance_id)
            .where(
                ContentCategoryRecord.id == category_id,
                ContentDraftRecord.is_shared.is_(True),
            )
        ).one_or_none()
        if row is None:
            return None
        category, draft, bot_name = row
        return SharedContentDraft(
            source_bot_instance_id=category.bot_instance_id,
            source_bot_name=bot_name,
            category=_category(category),
            draft=_draft(draft),
        )

    def get_category(self, bot_instance_id: int, category_id: int) -> ContentCategory | None:
        record = self._session.execute(
            select(ContentCategoryRecord).where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.id == category_id,
            )
        ).scalar_one_or_none()
        return _category(record) if record else None

    def get_category_by_slug(self, bot_instance_id: int, slug: str) -> ContentCategory | None:
        record = self._session.execute(
            select(ContentCategoryRecord).where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.slug == slug,
            )
        ).scalar_one_or_none()
        return _category(record) if record else None

    def get_home_category(self, bot_instance_id: int) -> ContentCategory | None:
        record = self._session.execute(
            select(ContentCategoryRecord).where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.is_home.is_(True),
            )
        ).scalar_one_or_none()
        return _category(record) if record else None

    def get_published_by_slug(self, bot_instance_id: int, slug: str) -> PublishedContent | None:
        row = self._session.execute(
            select(ContentCategoryRecord, ContentVersionRecord)
            .join(
                ContentVersionRecord,
                ContentVersionRecord.id == ContentCategoryRecord.published_version_id,
            )
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.slug == slug,
                ContentCategoryRecord.is_active.is_(True),
            )
        ).one_or_none()
        if row is None:
            return None
        category, version = row
        return PublishedContent(category=_category(category), version=_version(version))

    def get_published_by_category(
        self,
        bot_instance_id: int,
        category_id: int,
    ) -> PublishedContent | None:
        row = self._session.execute(
            select(ContentCategoryRecord, ContentVersionRecord)
            .join(
                ContentVersionRecord,
                ContentVersionRecord.id == ContentCategoryRecord.published_version_id,
            )
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.id == category_id,
                ContentCategoryRecord.is_active.is_(True),
            )
        ).one_or_none()
        if row is None:
            return None
        category, version = row
        return PublishedContent(category=_category(category), version=_version(version))

    def get_draft(self, bot_instance_id: int, category_id: int) -> ContentDraft | None:
        record = self._session.execute(
            select(ContentDraftRecord)
            .join(ContentCategoryRecord, ContentCategoryRecord.id == ContentDraftRecord.category_id)
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentDraftRecord.category_id == category_id,
            )
        ).scalar_one_or_none()
        return _draft(record) if record else None

    def create_category(
        self,
        category: ContentCategory,
        draft: ContentDraft | None,
        *,
        created_by: int | None,
    ) -> tuple[ContentCategory, ContentDraft | None]:
        category_record = ContentCategoryRecord(
            bot_instance_id=category.bot_instance_id,
            slug=category.slug,
            parent_id=category.parent_id,
            icon=category.icon,
            order=category.order,
            is_active=category.is_active,
            is_home=category.is_home,
            created_by=created_by,
            capability_key=category.capability_key,
            capability_view_key=category.capability_view_key,
            title=category.title,
            subtitle=category.subtitle,
            image_url=category.image_url,
        )
        self._session.add(category_record)
        self._session.flush()
        if draft is None:
            return _category(category_record), None
        draft_record = ContentDraftRecord(
            category_id=category_record.id,
            title=draft.title,
            subtitle=draft.subtitle,
            language=draft.language,
            blocks=clone_blocks(draft.blocks),
            revision=0,
            is_shared=draft.is_shared,
            updated_by=created_by,
            is_filled=draft.is_filled,
            image_url=draft.image_url,
            header_visible=draft.header_visible,
        )
        self._session.add(draft_record)
        self._session.flush()
        return _category(category_record), _draft(draft_record)

    def update_category(self, category: ContentCategory) -> ContentCategory:
        record = self._session.execute(
            select(ContentCategoryRecord).where(
                ContentCategoryRecord.id == category.id,
                ContentCategoryRecord.bot_instance_id == category.bot_instance_id,
            )
        ).scalar_one()
        record.icon = category.icon
        record.parent_id = category.parent_id
        record.order = category.order
        record.is_active = category.is_active
        record.title = category.title
        record.subtitle = category.subtitle
        record.image_url = category.image_url
        self._session.flush()
        return _category(record)

    def save_draft(
        self,
        bot_instance_id: int,
        draft: ContentDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> ContentDraft:
        record = self._session.execute(
            select(ContentDraftRecord)
            .join(ContentCategoryRecord, ContentCategoryRecord.id == ContentDraftRecord.category_id)
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentDraftRecord.category_id == draft.category_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(draft.category_id)
        if record.revision != expected_revision:
            raise DraftRevisionConflict
        record.title = draft.title
        record.subtitle = draft.subtitle
        record.language = draft.language
        record.blocks = clone_blocks(draft.blocks)
        record.revision += 1
        record.is_shared = draft.is_shared
        record.updated_by = updated_by
        record.is_filled = draft.is_filled
        record.image_url = draft.image_url
        record.header_visible = draft.header_visible
        self._session.flush()
        _sync_attachment_references(
            self._session,
            bot_instance_id=bot_instance_id,
            category_id=draft.category_id,
            scope="draft",
            blocks=record.blocks or [],
            image_url=record.image_url,
        )
        return _draft(record)

    def publish(
        self,
        bot_instance_id: int,
        category_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedContent:
        category_record = self._session.execute(
            select(ContentCategoryRecord)
            .where(
                ContentCategoryRecord.bot_instance_id == bot_instance_id,
                ContentCategoryRecord.id == category_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        draft_record = self._session.execute(
            select(ContentDraftRecord).where(ContentDraftRecord.category_id == category_id).with_for_update()
        ).scalar_one_or_none()
        if category_record is None or draft_record is None:
            raise LookupError(category_id)
        if draft_record.revision != expected_revision:
            raise DraftRevisionConflict
        if category_record.last_published_revision >= draft_record.revision:
            raise NothingToPublish
        version_number = (
            self._session.execute(
                select(func.max(ContentVersionRecord.version)).where(
                    ContentVersionRecord.category_id == category_id
                )
            ).scalar_one()
            or 0
        ) + 1
        version_record = ContentVersionRecord(
            category_id=category_id,
            version=version_number,
            source_revision=draft_record.revision,
            title=draft_record.title,
            subtitle=draft_record.subtitle,
            language=draft_record.language,
            blocks=clone_blocks(draft_record.blocks or []),
            published_by=published_by,
            published_at=datetime.now(tz=UTC),
            is_filled=draft_record.is_filled,
            image_url=draft_record.image_url,
            header_visible=draft_record.header_visible,
        )
        self._session.add(version_record)
        self._session.flush()
        category_record.published_version_id = version_record.id
        category_record.last_published_revision = draft_record.revision
        self._session.flush()
        _sync_attachment_references(
            self._session,
            bot_instance_id=bot_instance_id,
            category_id=category_id,
            scope="published",
            blocks=version_record.blocks or [],
            image_url=version_record.image_url,
        )
        return PublishedContent(
            category=_category(category_record),
            version=_version(version_record),
        )

    def reorder(self, bot_instance_id: int, category_ids: list[int]) -> list[ContentCategory]:
        records = list(
            self._session.execute(
                select(ContentCategoryRecord)
                .where(ContentCategoryRecord.bot_instance_id == bot_instance_id)
                .with_for_update()
            ).scalars()
        )
        if {record.id for record in records} != set(category_ids):
            raise ValueError("Category order must include every category in the current bot")
        by_id = {record.id: record for record in records}
        for order, category_id in enumerate(category_ids):
            by_id[category_id].order = order
        self._session.flush()
        return [_category(by_id[category_id]) for category_id in category_ids]


class SqlAlchemyContentReferenceGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def missing_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]:
        if not form_ids:
            return set()
        found = set(
            self._session.execute(
                select(FormTemplate.id).where(
                    FormTemplate.bot_instance_id == bot_instance_id,
                    FormTemplate.id.in_(form_ids),
                )
            ).scalars()
        )
        return form_ids - found

    def unready_form_ids(self, bot_instance_id: int, form_ids: set[int]) -> set[int]:
        if not form_ids:
            return set()
        ready = set(
            self._session.execute(
                select(FormTemplate.id).where(
                    FormTemplate.bot_instance_id == bot_instance_id,
                    FormTemplate.id.in_(form_ids),
                    FormTemplate.published_version_id.is_not(None),
                    FormTemplate.is_active.is_(True),
                    FormTemplate.is_archived.is_(False),
                )
            ).scalars()
        )
        return form_ids - ready

    def missing_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]:
        if not test_ids:
            return set()
        found = set(
            self._session.execute(
                select(TestDefinitionRecord.id).where(
                    TestDefinitionRecord.bot_instance_id == bot_instance_id,
                    TestDefinitionRecord.id.in_(test_ids),
                )
            ).scalars()
        )
        return test_ids - found

    def unready_test_ids(self, bot_instance_id: int, test_ids: set[int]) -> set[int]:
        if not test_ids:
            return set()
        ready = set(
            self._session.execute(
                select(TestDefinitionRecord.id).where(
                    TestDefinitionRecord.bot_instance_id == bot_instance_id,
                    TestDefinitionRecord.id.in_(test_ids),
                    TestDefinitionRecord.published_version_id.is_not(None),
                    TestDefinitionRecord.is_active.is_(True),
                    TestDefinitionRecord.is_archived.is_(False),
                )
            ).scalars()
        )
        return test_ids - ready

    def missing_attachment_ids(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> set[int]:
        if not attachment_ids:
            return set()
        found = set(
            self._session.execute(
                select(Attachment.id).where(
                    Attachment.bot_instance_id == bot_instance_id,
                    Attachment.id.in_(attachment_ids),
                )
            ).scalars()
        )
        return attachment_ids - found

    def attachment_mime_types(
        self,
        bot_instance_id: int,
        attachment_ids: set[int],
    ) -> dict[int, str]:
        if not attachment_ids:
            return {}
        rows = self._session.execute(
            select(Attachment.id, Attachment.mime).where(
                Attachment.bot_instance_id == bot_instance_id,
                Attachment.id.in_(attachment_ids),
            )
        ).all()
        return {attachment_id: mime for attachment_id, mime in rows}

    def missing_capability_views(
        self,
        bot_instance_id: int,
        references: set[tuple[str, str]],
    ) -> set[tuple[str, str]]:
        if not references:
            return set()
        keys = {key for key, _ in references}
        installations = {
            record.capability_key: record
            for record in self._session.execute(
                select(CapabilityInstallationRecord).where(
                    CapabilityInstallationRecord.bot_instance_id == bot_instance_id,
                    CapabilityInstallationRecord.capability_key.in_(keys),
                    CapabilityInstallationRecord.is_enabled.is_(True),
                )
            ).scalars()
        }
        missing: set[tuple[str, str]] = set()
        for key, view_key in references:
            installation = installations.get(key)
            if installation is None:
                missing.add((key, view_key))
                continue
            try:
                descriptor = capability_registry.get(key)
                descriptor.get_view(view_key)
                descriptor.validate_config(installation.config)
            except (LookupError, ValueError):
                missing.add((key, view_key))
        return missing


def _form_is_ready(definition: FormDefinition) -> bool:
    return (
        definition.published_version_id is not None
        and definition.is_active
        and not definition.is_archived
    )


class FormContentTemplateDependencyGateway:
    def __init__(self, form_repository: FormRepository) -> None:
        self._forms = form_repository

    def inspect(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
    ) -> SharedContentDependencyReport:
        form_ids, attachment_ids = extract_references(blocks)
        target_rows = self._forms.list_forms(target_bot_instance_id)
        target_by_slug = {definition.slug: definition for definition, _ in target_rows}
        targets: list[FormDependencyTarget] = []
        for definition, draft in target_rows:
            if definition.id is None or not _form_is_ready(definition):
                continue
            published = self._forms.get_published(target_bot_instance_id, definition.id)
            targets.append(
                FormDependencyTarget(
                    id=definition.id,
                    slug=definition.slug,
                    label=published.version.name if published else draft.name,
                )
            )

        dependencies: list[FormDependency] = []
        for source_id in sorted(form_ids):
            source_definition = self._forms.get_form(source_bot_instance_id, source_id)
            source_draft = self._forms.get_draft(source_bot_instance_id, source_id)
            if source_definition is None or source_draft is None:
                dependencies.append(
                    FormDependency(
                        source_id=source_id,
                        source_slug=None,
                        label=f"Форма #{source_id}",
                        status="unavailable",
                        source_is_shared=False,
                    )
                )
                continue
            shared = self._forms.get_shared_draft(source_id)
            source_is_shared = bool(
                shared and shared.source_bot_instance_id == source_bot_instance_id
            )
            matched = target_by_slug.get(source_definition.slug)
            dependencies.append(
                FormDependency(
                    source_id=source_id,
                    source_slug=source_definition.slug,
                    label=source_draft.name,
                    status=(
                        "resolved"
                        if matched is not None
                        else "copy_available"
                        if source_is_shared
                        else "mapping_required"
                    ),
                    source_is_shared=source_is_shared,
                    matched_target_id=matched.id if matched else None,
                    matched_target_ready=_form_is_ready(matched) if matched else False,
                )
            )
        blockers = (
            [
                DependencyBlocker(
                    kind="file",
                    code="file_copy_not_supported",
                    count=len(attachment_ids),
                )
            ]
            if attachment_ids
            else []
        )
        return SharedContentDependencyReport(
            form_dependencies=dependencies,
            form_targets=targets,
            blockers=blockers,
        )

    def _resolve_explicit_form(
        self,
        *,
        dependency: FormDependency,
        resolution: FormDependencyResolution,
        target_bot_instance_id: int,
        created_by: int | None,
        order: int,
    ) -> tuple[int, str, bool]:
        if resolution.action == "use_existing":
            if resolution.target_id is None:
                raise ContentDependencyResolutionInvalid("Выберите форму текущего бота")
            target = self._forms.get_form(target_bot_instance_id, resolution.target_id)
            if target is None or target.id is None or not _form_is_ready(target):
                raise ContentDependencyResolutionInvalid(
                    "Выбранная форма должна быть опубликована, активна и принадлежать текущему боту"
                )
            return target.id, "use_existing", True
        if resolution.target_id is not None:
            raise ContentDependencyResolutionInvalid(
                "При копировании общего черновика нельзя указывать целевую форму"
            )
        if not dependency.source_is_shared or not dependency.source_slug:
            raise ContentDependencyResolutionInvalid(
                f"Форма #{dependency.source_id} не расшарена и не может быть скопирована"
            )
        if self._forms.get_form_by_slug(target_bot_instance_id, dependency.source_slug):
            raise ContentDependencyResolutionInvalid(
                "Состояние форм изменилось. Обновите мастер зависимостей"
            )
        definition, _ = ImportSharedFormDraft(self._forms).execute(
            ImportSharedFormDraftCommand(
                bot_instance_id=target_bot_instance_id,
                source_form_id=dependency.source_id,
                slug=dependency.source_slug,
                order=order,
                created_by=created_by,
            )
        )
        if definition.id is None:
            raise ContentDependencyResolutionInvalid(
                "Ошибка при создании копии формы"
            )
        return definition.id, "copy_shared", False

    def resolve(
        self,
        *,
        source_bot_instance_id: int,
        target_bot_instance_id: int,
        blocks: list[dict],
        form_resolutions: tuple[FormDependencyResolution, ...],
        created_by: int | None,
    ) -> ContentDependencyResolutionResult:
        report = self.inspect(
            source_bot_instance_id=source_bot_instance_id,
            target_bot_instance_id=target_bot_instance_id,
            blocks=blocks,
        )
        if report.blockers:
            raise SharedContentContainsFiles
        dependencies_by_id = {item.source_id: item for item in report.form_dependencies}
        resolutions_by_id = {item.source_id: item for item in form_resolutions}
        extra_ids = set(resolutions_by_id) - set(dependencies_by_id)
        if extra_ids:
            raise ContentDependencyResolutionInvalid(
                f"Получены неизвестные зависимости форм: {sorted(extra_ids)}"
            )

        existing_target_rows = self._forms.list_forms(target_bot_instance_id)
        next_order = max(
            (definition.order for definition, _ in existing_target_rows),
            default=-1,
        ) + 1
        mapping: dict[int, int] = {}
        resolved_dependencies: list[ResolvedFormDependency] = []
        for dependency in report.form_dependencies:
            if dependency.status == "unavailable":
                raise ContentDependencyResolutionInvalid(
                    f"Исходная форма #{dependency.source_id} недоступна"
                )
            resolution = resolutions_by_id.get(dependency.source_id)
            if resolution is None:
                if dependency.matched_target_id is None:
                    raise ContentDependencyResolutionInvalid(
                        f"Для формы #{dependency.source_id} выберите существующую форму текущего бота"
                    )
                target_id = dependency.matched_target_id
                action = "matched_slug"
                target_ready = dependency.matched_target_ready
            else:
                target_id, action, target_ready = self._resolve_explicit_form(
                    dependency=dependency,
                    resolution=resolution,
                    target_bot_instance_id=target_bot_instance_id,
                    created_by=created_by,
                    order=next_order,
                )
                if action == "copy_shared":
                    next_order += 1
            mapping[dependency.source_id] = target_id
            resolved_dependencies.append(
                ResolvedFormDependency(
                    source_id=dependency.source_id,
                    target_id=target_id,
                    action=action,
                    target_ready=target_ready,
                )
            )
        return ContentDependencyResolutionResult(
            blocks=remap_form_references(blocks, mapping),
            form_dependencies=resolved_dependencies,
        )


def build_form_content_template_dependency_gateway(
    session: Session,
) -> FormContentTemplateDependencyGateway:
    """Composition point for wiring forms' infrastructure into content's own gateway —
    keeps `SqlAlchemyFormRepository` out of content's presentation layer, which used to
    import and construct it directly (Task 053 audit finding #6)."""
    return FormContentTemplateDependencyGateway(SqlAlchemyFormRepository(session))


def get_available_bot_slug(session: Session, bot_instance_id: int) -> str | None:
    """The bot's slug if it exists and is not soft-deleted, else None — backs the public,
    token-gated content-preview endpoint's existence check (and its response's `bot_slug`
    field) without that presentation-layer router needing to import bot_instances'
    infrastructure repository directly (Task 053 audit finding #6)."""
    record = session.get(BotInstanceRecord, bot_instance_id)
    if record is None or record.deleted_at is not None:
        return None
    return record.slug


class SqlAlchemyContentAssetCatalog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_admin_attachments(
        self,
        bot_instance_id: int,
        *,
        limit: int,
        offset: int,
        mime_family: str | None = None,
        search: str | None = None,
    ) -> ContentAttachmentPage:
        conditions = [
            Attachment.bot_instance_id == bot_instance_id,
            Attachment.uploaded_by_admin_id.is_not(None),
        ]
        if mime_family == "image":
            conditions.append(Attachment.mime.like("image/%"))
        elif mime_family == "other":
            conditions.append(~Attachment.mime.like("image/%"))
        if search:
            conditions.append(Attachment.original_name.ilike(f"%{search}%"))

        total = self._session.execute(
            select(func.count()).select_from(Attachment).where(*conditions)
        ).scalar_one()
        records = list(
            self._session.execute(
                select(Attachment)
                .where(*conditions)
                .order_by(Attachment.created_at.desc(), Attachment.id.desc())
                .limit(limit)
                .offset(offset)
            ).scalars()
        )

        attachment_ids = {record.id for record in records}
        references_by_attachment: dict[int, dict[str, list[AttachmentReference]]] = {}
        if attachment_ids:
            reference_rows = self._session.execute(
                select(
                    ContentAttachmentReferenceRecord.attachment_id,
                    ContentAttachmentReferenceRecord.scope,
                    ContentAttachmentReferenceRecord.category_id,
                    ContentAttachmentReferenceRecord.usage,
                ).where(
                    ContentAttachmentReferenceRecord.bot_instance_id == bot_instance_id,
                    ContentAttachmentReferenceRecord.attachment_id.in_(attachment_ids),
                )
            ).all()
            for attachment_id, scope, category_id, usage in reference_rows:
                bucket = references_by_attachment.setdefault(attachment_id, {"draft": [], "published": []})
                bucket[scope].append(AttachmentReference(category_id=category_id, usage=usage))

        items = [
            ContentAttachment(
                id=record.id,
                name=record.original_name,
                mime=record.mime,
                size_bytes=record.size_bytes,
                created_at=record.created_at,
                referenced_by_draft=tuple(
                    references_by_attachment.get(record.id, {}).get("draft", [])
                ),
                referenced_by_published=tuple(
                    references_by_attachment.get(record.id, {}).get("published", [])
                ),
            )
            for record in records
        ]
        return ContentAttachmentPage(items=items, total=total)

    def delete_admin_attachment(self, bot_instance_id: int, attachment_id: int) -> DeletedAttachment:
        record = self._session.execute(
            select(Attachment).where(
                Attachment.bot_instance_id == bot_instance_id,
                Attachment.id == attachment_id,
                Attachment.uploaded_by_admin_id.is_not(None),
            )
        ).scalar_one_or_none()
        if record is None:
            raise ContentAttachmentNotFound(str(attachment_id))
        published_category_ids = sorted(
            set(
                self._session.execute(
                    select(ContentAttachmentReferenceRecord.category_id).where(
                        ContentAttachmentReferenceRecord.attachment_id == attachment_id,
                        ContentAttachmentReferenceRecord.scope == "published",
                    )
                ).scalars()
            )
        )
        if published_category_ids:
            raise ContentAttachmentInUse(published_category_ids)
        result = DeletedAttachment(
            id=record.id,
            name=record.original_name,
            mime=record.mime,
            size_bytes=record.size_bytes,
        )
        # Reference rows (draft-scope included) and the Attachment row's other FKs cascade via
        # ON DELETE CASCADE; only the on-disk bytes need an explicit delete.
        delete_file(record.storage_path)
        self._session.delete(record)
        self._session.flush()
        return result

    def list_published_forms(self, bot_instance_id: int) -> list[ContentFormOption]:
        rows = self._session.execute(
            select(FormTemplate.id, FormVersionRecord.name)
            .join(
                FormVersionRecord,
                FormVersionRecord.id == FormTemplate.published_version_id,
            )
            .where(
                FormTemplate.bot_instance_id == bot_instance_id,
                FormTemplate.is_active.is_(True),
                FormTemplate.is_archived.is_(False),
            )
            .order_by(FormTemplate.order, FormTemplate.id)
        ).all()
        return [ContentFormOption(id=form_id, name=name) for form_id, name in rows]

    def list_published_tests(self, bot_instance_id: int) -> list[ContentTestOption]:
        rows = self._session.execute(
            select(TestDefinitionRecord.id, TestVersionRecord.name)
            .join(
                TestVersionRecord,
                TestVersionRecord.id == TestDefinitionRecord.published_version_id,
            )
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.is_active.is_(True),
                TestDefinitionRecord.is_archived.is_(False),
            )
            .order_by(TestDefinitionRecord.order, TestDefinitionRecord.id)
        ).all()
        return [ContentTestOption(id=test_id, name=name) for test_id, name in rows]


class SqlAlchemyContentAnalyticsGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_category_open(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
    ) -> None:
        self._session.add(
            UserAction(
                bot_instance_id=bot_instance_id,
                user_id=user_id,
                action_type="content_category_open",
                category_id=category_id,
                content_version_id=version_id,
                source_surface="legacy",
            )
        )

    def record_tab_open(
        self,
        *,
        bot_instance_id: int,
        user_id: int,
        category_id: int,
        version_id: int,
        tab_key: str,
    ) -> None:
        self._session.add(
            UserAction(
                bot_instance_id=bot_instance_id,
                user_id=user_id,
                action_type="content_tab_open",
                category_id=category_id,
                content_version_id=version_id,
                tab_key=tab_key,
                source_surface="legacy",
            )
        )
