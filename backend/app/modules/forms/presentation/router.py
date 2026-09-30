from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ....core.errors import bad_request, conflict, not_found
from ....db.session import get_db
from ....modules.audit.infrastructure.models import AuditLog
from ....modules.bot_instances.domain.entities import BotInstance
from ....modules.maintenance.presentation.dependencies import enforce_user_access_available
from ....modules.tenancy.presentation.dependencies import require_tenant_access
from ....services.ws_hub import hub, staff_room
from ..application.commands import (
    CreateFormCommand,
    ImportSharedFormDraftCommand,
    PublishFormCommand,
    SaveFormDraftCommand,
    UpdateFormCommand,
)
from ..application.use_cases import (
    CreateForm,
    FormDraftRevisionConflict,
    FormNotAvailable,
    FormNotFound,
    FormSlugExists,
    FormVersionMismatch,
    GetFormDraft,
    GetPublishedForm,
    ImportSharedFormDraft,
    ListForms,
    ListPublishedForms,
    ListSharedFormDrafts,
    NothingToPublish,
    PublishForm,
    ReorderForms,
    SaveFormDraft,
    UpdateForm,
)
from ..domain.entities import FormDefinition, FormDraft, PublishedForm
from ..domain.fields import FormSchemaValidationError
from ..infrastructure.repositories import SqlAlchemyFormRepository
from .dependencies import FormManagerContext, require_form_manager, require_form_reader
from .schemas import (
    AdminFormResponse,
    FormCreateRequest,
    FormDraftResponse,
    FormDraftSaveRequest,
    FormPatchRequest,
    FormPublishRequest,
    FormReorderRequest,
    PublishedFormResponse,
    PublishedFormSummaryResponse,
    SharedFormDraftImportRequest,
    SharedFormDraftResponse,
)

router = APIRouter()


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _draft_response(draft: FormDraft) -> FormDraftResponse:
    return FormDraftResponse(
        form_id=draft.form_definition_id,
        name=draft.name,
        description=draft.description,
        reply_on_accept=draft.reply_on_accept,
        fields=draft.fields,
        revision=draft.revision,
        is_shared=draft.is_shared,
    )


def _admin_response(definition: FormDefinition, draft: FormDraft) -> AdminFormResponse:
    assert definition.id is not None
    return AdminFormResponse(
        id=definition.id,
        slug=definition.slug,
        order=definition.order,
        is_active=definition.is_active,
        show_in_catalog=definition.show_in_catalog,
        is_archived=definition.is_archived,
        published_version_id=definition.published_version_id,
        last_published_revision=definition.last_published_revision,
        draft=_draft_response(draft),
    )


def _summary(published: PublishedForm) -> PublishedFormSummaryResponse:
    assert published.definition.id is not None and published.version.id is not None
    return PublishedFormSummaryResponse(
        id=published.definition.id,
        slug=published.definition.slug,
        order=published.definition.order,
        name=published.version.name,
        description=published.version.description,
        version_id=published.version.id,
        version=published.version.version,
    )


def _published_response(published: PublishedForm) -> PublishedFormResponse:
    return PublishedFormResponse(
        **_summary(published).model_dump(),
        reply_on_accept=published.version.reply_on_accept,
        fields=published.version.fields,
        published_at=published.version.published_at,
    )


def _raise_form_error(exc: Exception) -> None:
    if isinstance(exc, FormNotFound):
        raise not_found("Form not found", code="form_not_found") from exc
    if isinstance(exc, FormSlugExists):
        raise conflict("Form slug already exists", code="form_slug_exists") from exc
    if isinstance(exc, FormDraftRevisionConflict):
        raise conflict(
            "Draft was changed by another editor",
            code="form_draft_revision_conflict",
        ) from exc
    if isinstance(exc, NothingToPublish):
        raise conflict("Draft has no unpublished changes", code="nothing_to_publish") from exc
    if isinstance(exc, FormNotAvailable):
        raise conflict("Form is not available", code="form_not_available") from exc
    if isinstance(exc, FormVersionMismatch):
        raise conflict("Form version does not belong to this form", code="form_version_mismatch") from exc
    if isinstance(exc, FormSchemaValidationError):
        raise bad_request(str(exc), code="invalid_form_schema", path=exc.path) from exc
    if isinstance(exc, ValueError):
        raise bad_request(str(exc), code="invalid_form") from exc
    raise exc


def _audit(
    db: Session,
    *,
    admin_id: int | None,
    bot_instance_id: int,
    form_id: int | None,
    action: str,
    revision: int | None = None,
    version_id: int | None = None,
    form_ids: list[int] | None = None,
    source_form_id: int | None = None,
) -> None:
    path = f"/api/forms/admin/{form_id}" if form_id is not None else "/api/forms/admin/reorder"
    meta = {
        "action": action,
        "bot_instance_id": bot_instance_id,
        "revision": revision,
        "version_id": version_id,
    }
    if form_id is not None:
        meta["form_id"] = form_id
    if form_ids is not None:
        meta["form_ids"] = form_ids
    if source_form_id is not None:
        meta["source_form_id"] = source_form_id
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_instance_id,
            method="FORM",
            path=path,
            status_code=200,
            meta=meta,
        )
    )


async def _broadcast_forms_changed(bot_instance_id: int) -> None:
    await hub.broadcast(staff_room(bot_instance_id), {"type": "forms_changed"})


@router.get("/admin", response_model=list[AdminFormResponse])
def list_admin_forms(
    context: FormManagerContext = Depends(require_form_reader),
    db: Session = Depends(get_db),
) -> list[AdminFormResponse]:
    items = ListForms(SqlAlchemyFormRepository(db)).execute(_bot_id(context.bot))
    return [_admin_response(definition, draft) for definition, draft in items]


@router.post("/admin", response_model=AdminFormResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_form(
    payload: FormCreateRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> AdminFormResponse:
    try:
        definition, draft = CreateForm(SqlAlchemyFormRepository(db)).execute(
            CreateFormCommand(
                bot_instance_id=_bot_id(context.bot),
                created_by=context.principal.admin_id,
                **payload.model_dump(),
            )
        )
        assert definition.id is not None
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=definition.id,
            action="form_created",
            revision=draft.revision,
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return _admin_response(definition, draft)


@router.post("/admin/reorder", response_model=list[AdminFormResponse])
async def reorder_admin_forms(
    payload: FormReorderRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> list[AdminFormResponse]:
    repository = SqlAlchemyFormRepository(db)
    try:
        ReorderForms(repository).execute(_bot_id(context.bot), payload.form_ids)
        items = ListForms(repository).execute(_bot_id(context.bot))
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=None,
            form_ids=payload.form_ids,
            action="forms_reordered",
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return [_admin_response(definition, draft) for definition, draft in items]


@router.get("/admin/shared-drafts", response_model=list[SharedFormDraftResponse])
def list_shared_form_drafts(
    _: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> list[SharedFormDraftResponse]:
    items = ListSharedFormDrafts(SqlAlchemyFormRepository(db)).execute()
    return [
        SharedFormDraftResponse(
            source_form_id=item.definition.id,
            source_bot_instance_id=item.source_bot_instance_id,
            source_bot_name=item.source_bot_name,
            slug=item.definition.slug,
            name=item.draft.name,
            description=item.draft.description,
        )
        for item in items
        if item.definition.id is not None
    ]


@router.post(
    "/admin/shared-drafts/{source_form_id}/import",
    response_model=AdminFormResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_shared_form_draft(
    source_form_id: int,
    payload: SharedFormDraftImportRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> AdminFormResponse:
    try:
        definition, draft = ImportSharedFormDraft(SqlAlchemyFormRepository(db)).execute(
            ImportSharedFormDraftCommand(
                bot_instance_id=_bot_id(context.bot),
                source_form_id=source_form_id,
                slug=payload.slug,
                order=payload.order,
                created_by=context.principal.admin_id,
            )
        )
        assert definition.id is not None
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=definition.id,
            source_form_id=source_form_id,
            action="shared_form_draft_imported",
            revision=draft.revision,
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return _admin_response(definition, draft)


@router.patch("/admin/{form_id}", response_model=AdminFormResponse)
async def patch_admin_form(
    form_id: int,
    payload: FormPatchRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> AdminFormResponse:
    repository = SqlAlchemyFormRepository(db)
    try:
        definition = UpdateForm(repository).execute(
            UpdateFormCommand(
                bot_instance_id=_bot_id(context.bot),
                form_id=form_id,
                **payload.model_dump(exclude_unset=True),
            )
        )
        draft = GetFormDraft(repository).execute(_bot_id(context.bot), form_id)
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=form_id,
            action=(
                "form_archived"
                if payload.is_archived is True
                else "form_restored"
                if payload.is_archived is False
                else "form_activated"
                if payload.is_active is True
                else "form_updated"
            ),
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return _admin_response(definition, draft)


@router.get("/admin/{form_id}/draft", response_model=FormDraftResponse)
def get_admin_form_draft(
    form_id: int,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> FormDraftResponse:
    try:
        draft = GetFormDraft(SqlAlchemyFormRepository(db)).execute(_bot_id(context.bot), form_id)
    except Exception as exc:
        _raise_form_error(exc)
    return _draft_response(draft)


@router.put("/admin/{form_id}/draft", response_model=FormDraftResponse)
async def save_admin_form_draft(
    form_id: int,
    payload: FormDraftSaveRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> FormDraftResponse:
    try:
        draft = SaveFormDraft(SqlAlchemyFormRepository(db)).execute(
            SaveFormDraftCommand(
                bot_instance_id=_bot_id(context.bot),
                form_id=form_id,
                updated_by=context.principal.admin_id,
                **payload.model_dump(mode="json"),
            )
        )
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=form_id,
            action="form_draft_saved",
            revision=draft.revision,
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return _draft_response(draft)


@router.post("/admin/{form_id}/publish", response_model=PublishedFormResponse)
async def publish_admin_form(
    form_id: int,
    payload: FormPublishRequest,
    context: FormManagerContext = Depends(require_form_manager),
    db: Session = Depends(get_db),
) -> PublishedFormResponse:
    try:
        published = PublishForm(SqlAlchemyFormRepository(db)).execute(
            PublishFormCommand(
                bot_instance_id=_bot_id(context.bot),
                form_id=form_id,
                expected_revision=payload.expected_revision,
                published_by=context.principal.admin_id,
            )
        )
        _audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            form_id=form_id,
            action="form_published",
            revision=published.version.source_revision,
            version_id=published.version.id,
        )
        db.commit()
        await _broadcast_forms_changed(_bot_id(context.bot))
    except Exception as exc:
        db.rollback()
        _raise_form_error(exc)
    return _published_response(published)


@router.get(
    "",
    response_model=list[PublishedFormSummaryResponse],
    dependencies=[Depends(enforce_user_access_available)],
)
def list_published_forms(
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[PublishedFormSummaryResponse]:
    items = ListPublishedForms(SqlAlchemyFormRepository(db)).execute(_bot_id(bot))
    return [_summary(item) for item in items]


@router.get(
    "/{form_id}",
    response_model=PublishedFormResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def get_published_form(
    form_id: int,
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> PublishedFormResponse:
    try:
        published = GetPublishedForm(SqlAlchemyFormRepository(db)).execute(_bot_id(bot), form_id)
    except Exception as exc:
        _raise_form_error(exc)
    return _published_response(published)


@router.get(
    "/{form_id}/versions/{version_id}",
    response_model=PublishedFormResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def get_published_form_version(
    form_id: int,
    version_id: int,
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> PublishedFormResponse:
    try:
        published = GetPublishedForm(SqlAlchemyFormRepository(db)).execute(_bot_id(bot), form_id, version_id)
    except Exception as exc:
        _raise_form_error(exc)
    return _published_response(published)
