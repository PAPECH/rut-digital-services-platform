from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_student
from ....core.errors import bad_request, conflict, forbidden, not_found
from ....core.security import create_access_token
from ....db.session import get_db
from ....modules.audit.infrastructure.models import AuditLog
from ....modules.bot_instances.domain.entities import BotInstance
from ....modules.maintenance.presentation.dependencies import enforce_user_access_available
from ....modules.tenancy.presentation.dependencies import require_tenant_access
from ....services.content_preview_tokens import (
    InvalidPreviewToken,
    make_preview_token,
    verify_preview_token,
)
from ....services.files import make_signed_url
from ..application.commands import (
    CreateCategoryCommand,
    ImportSharedContentDraftCommand,
    PublishContentCommand,
    SaveDraftCommand,
    UpdateCategoryCommand,
)
from ..application.dependencies import (
    ContentDependencyCopyForbidden,
    ContentDependencyResolutionInvalid,
    FormDependencyResolution,
    ResolvedFormDependency,
    SharedContentDependencyReport,
)
from ..application.use_cases import (
    ContentAttachmentInUse,
    ContentAttachmentNotFound,
    ContentDependenciesNotReady,
    ContentIsCapabilityShortcut,
    ContentNotFound,
    ContentSlugExists,
    ContentTabNotFound,
    CreateContentCategory,
    CrossTenantReference,
    DeleteContentAttachment,
    DraftRevisionConflict,
    GetContentDraft,
    GetOrCreateHomeCategory,
    GetPublishedContent,
    GetSharedContentDependencies,
    ImportSharedContentDraft,
    InvalidCategoryParent,
    InvalidInlineImageAttachment,
    ListContentAttachments,
    ListContentCategories,
    ListContentForms,
    ListContentTests,
    ListPublishedContent,
    ListSharedContentDrafts,
    NothingToPublish,
    PublishContent,
    PublishedVersionMismatch,
    RecordContentCategoryOpen,
    RecordContentTabOpen,
    ReorderContentCategories,
    SaveContentDraft,
    SharedContentContainsFiles,
    ShortcutCannotHaveChildren,
    ShortcutPointerIncomplete,
    UpdateContentCategory,
)
from ..domain.blocks import BlockValidationError, extract_references
from ..domain.entities import ContentAttachment, ContentCategory, ContentDraft, PublishedContent
from ..infrastructure.repositories import (
    SqlAlchemyContentAnalyticsGateway,
    SqlAlchemyContentAssetCatalog,
    SqlAlchemyContentReferenceGateway,
    SqlAlchemyContentRepository,
    build_form_content_template_dependency_gateway,
    get_available_bot_slug,
)
from .dependencies import (
    ContentManagerContext,
    can_manage_form_dependencies,
    require_content_manager,
)
from .schemas import (
    AdminCategoryResponse,
    AttachmentUrlEntry,
    CategoryCreateRequest,
    CategoryPatchRequest,
    ContentAttachmentListResponse,
    ContentAttachmentReferenceResponse,
    ContentAttachmentResponse,
    ContentDependencyBlockerResponse,
    ContentFormOptionResponse,
    ContentOpenEventRequest,
    ContentTabOpenEventRequest,
    ContentTestOptionResponse,
    DraftPreviewResponse,
    DraftResponse,
    DraftSaveRequest,
    PreviewTokenResponse,
    FormDependencyTargetResponse,
    PublishedCategorySummaryResponse,
    PublishedContentResponse,
    PublishRequest,
    ReorderRequest,
    ResolvedFormDependencyResponse,
    SharedContentDependenciesResponse,
    SharedContentDraftImportRequest,
    SharedContentDraftImportResponse,
    SharedContentDraftResponse,
    SharedContentFormDependencyResponse,
)

router = APIRouter()


def _bot_id(bot: BotInstance) -> int:
    if bot.id is None:
        raise not_found("Bot instance not found", code="bot_not_found")
    return bot.id


def _draft_response(draft: ContentDraft) -> DraftResponse:
    return DraftResponse(
        category_id=draft.category_id,
        title=draft.title,
        subtitle=draft.subtitle,
        language=draft.language,
        blocks=draft.blocks,
        revision=draft.revision,
        is_shared=draft.is_shared,
        is_filled=draft.is_filled,
        image_url=draft.image_url,
        header_visible=draft.header_visible,
    )


def _admin_category_response(
    category: ContentCategory,
    draft: ContentDraft | None,
) -> AdminCategoryResponse:
    assert category.id is not None
    return AdminCategoryResponse(
        id=category.id,
        slug=category.slug,
        parent_id=category.parent_id,
        icon=category.icon,
        order=category.order,
        is_active=category.is_active,
        published_version_id=category.published_version_id,
        last_published_revision=category.last_published_revision,
        is_home=category.is_home,
        draft=_draft_response(draft) if draft is not None else None,
        capability_key=category.capability_key,
        capability_view_key=category.capability_view_key,
        title=category.title,
        subtitle=category.subtitle,
        image_url=category.image_url,
    )


def _published_summary(content: PublishedContent) -> PublishedCategorySummaryResponse:
    category = content.category
    assert category.id is not None
    if content.version is None:
        # A capability shortcut: no version exists, so its own card fields (set at
        # creation/edit, not through a draft/publish cycle) are the source of truth.
        assert category.is_shortcut
        return PublishedCategorySummaryResponse(
            id=category.id,
            slug=category.slug,
            parent_id=category.parent_id,
            icon=category.icon,
            order=category.order,
            title=category.title or "",
            subtitle=category.subtitle,
            version_id=None,
            version=None,
            is_filled=False,
            image_url=category.image_url,
            header_visible=True,
            is_home=False,
            capability_key=category.capability_key,
            capability_view_key=category.capability_view_key,
        )
    assert content.version.id is not None
    return PublishedCategorySummaryResponse(
        id=category.id,
        slug=category.slug,
        parent_id=category.parent_id,
        icon=category.icon,
        order=category.order,
        title=content.version.title,
        subtitle=content.version.subtitle,
        version_id=content.version.id,
        version=content.version.version,
        is_filled=content.version.is_filled,
        image_url=content.version.image_url,
        header_visible=content.version.header_visible,
        is_home=category.is_home,
        capability_key=None,
        capability_view_key=None,
    )


def _attachment_urls(
    db: Session,
    *,
    bot_instance_id: int,
    attachment_ids: set[int],
) -> dict[int, AttachmentUrlEntry]:
    """Card images, file_list tiles/inline images -- every attachment a bot's public content
    hands out -- are public bot assets with no session of their own, so their signed URLs must
    never expire (ttl_seconds=-1); an admin or end user should never see a broken image because
    a link timed out."""
    mime_types = SqlAlchemyContentReferenceGateway(db).attachment_mime_types(
        bot_instance_id, attachment_ids
    )
    return {
        file_id: AttachmentUrlEntry(
            url=make_signed_url(file_id, ttl_seconds=-1),
            mime=mime_types.get(file_id, "application/octet-stream"),
        )
        for file_id in attachment_ids
    }


def _published_response(content: PublishedContent, db: Session) -> PublishedContentResponse:
    summary = _published_summary(content)
    if content.version is None:
        # A capability shortcut has no page content to serve -- callers that need a full
        # `PublishedContentResponse` (the mini-app's /catalog prefetch) get an empty page body;
        # the tile itself is rendered from the summary fields plus the platform manifest.
        return PublishedContentResponse(
            **summary.model_dump(),
            language="ru",
            blocks=[],
            attachment_urls={},
            published_at=datetime.now(tz=timezone.utc),
        )
    _, attachment_ids = extract_references(content.version.blocks)
    return PublishedContentResponse(
        **summary.model_dump(),
        language=content.version.language,
        blocks=content.version.blocks,
        attachment_urls=_attachment_urls(
            db, bot_instance_id=content.category.bot_instance_id, attachment_ids=attachment_ids
        ),
        published_at=content.version.published_at,
    )


def _raise_dependency_error(exc: Exception) -> None:
    if isinstance(exc, ContentDependencyResolutionInvalid):
        raise bad_request(
            str(exc),
            code="content_dependency_resolution_invalid",
        ) from exc
    if isinstance(exc, ContentDependencyCopyForbidden):
        raise forbidden(
            "Для копирования формы нужны права на управление формами",
            code="content_dependency_copy_forbidden",
        ) from exc


def _raise_reference_error(exc: Exception) -> None:
    if isinstance(exc, CrossTenantReference):
        raise bad_request(
            "Content contains missing or cross-tenant references",
            code="cross_tenant_reference",
            form_ids=sorted(exc.form_ids),
            attachment_ids=sorted(exc.attachment_ids),
            capability_views=[
                {"capability_key": key, "view_key": view} for key, view in sorted(exc.capability_views)
            ],
            category_ids=sorted(exc.category_ids),
            test_ids=sorted(exc.test_ids),
        ) from exc
    if isinstance(exc, InvalidInlineImageAttachment):
        raise bad_request(
            "display_mode=inline_image требует attachment с mime image/*",
            code="invalid_inline_image_attachment",
            attachment_ids=sorted(exc.attachment_ids),
        ) from exc


def _raise_content_error(exc: Exception) -> None:
    _raise_dependency_error(exc)
    _raise_reference_error(exc)
    if isinstance(exc, ContentIsCapabilityShortcut):
        raise not_found(
            "Category is a capability shortcut, not a content page",
            code="content_is_capability_shortcut",
            capability_key=exc.capability_key,
            view_key=exc.view_key,
        ) from exc
    if isinstance(exc, ShortcutPointerIncomplete):
        raise bad_request(str(exc), code="shortcut_pointer_incomplete") from exc
    if isinstance(exc, ShortcutCannotHaveChildren):
        raise bad_request(str(exc), code="shortcut_cannot_have_children") from exc
    if isinstance(exc, ContentNotFound):
        raise not_found("Content category not found", code="content_not_found") from exc
    if isinstance(exc, ContentSlugExists):
        raise conflict("Category slug already exists", code="slug_exists") from exc
    if isinstance(exc, DraftRevisionConflict):
        raise conflict(
            "Draft was changed by another editor",
            code="draft_revision_conflict",
        ) from exc
    if isinstance(exc, NothingToPublish):
        raise conflict("Draft has no unpublished changes", code="nothing_to_publish") from exc
    if isinstance(exc, ContentDependenciesNotReady):
        raise conflict(
            "Перед публикацией категории опубликуйте и активируйте связанные формы и тесты",
            code="content_dependencies_not_ready",
            form_ids=sorted(exc.form_ids),
            test_ids=sorted(exc.test_ids),
        ) from exc
    if isinstance(exc, BlockValidationError):
        raise bad_request(str(exc), code="invalid_block", path=exc.path) from exc
    if isinstance(exc, PublishedVersionMismatch):
        raise conflict(
            "Published content version is no longer current",
            code="published_version_mismatch",
        ) from exc
    if isinstance(exc, ContentTabNotFound):
        raise bad_request("Content tab not found", code="content_tab_not_found") from exc
    if isinstance(exc, InvalidCategoryParent):
        raise bad_request(str(exc), code="invalid_category_parent") from exc
    if isinstance(exc, SharedContentContainsFiles):
        raise bad_request(
            "Общий черновик не может содержать файлы текущего бота",
            code="shared_content_contains_files",
        ) from exc
    if isinstance(exc, ValueError):
        raise bad_request(str(exc), code="invalid_content") from exc
    raise exc


def _add_content_audit(
    db: Session,
    *,
    admin_id: int | None,
    bot_instance_id: int,
    category_id: int,
    action: str,
    version_id: int | None = None,
    source_category_id: int | None = None,
    form_dependencies: list[ResolvedFormDependency] | None = None,
) -> None:
    meta = {
        "action": action,
        "bot_instance_id": bot_instance_id,
        "category_id": category_id,
        "version_id": version_id,
    }
    if source_category_id is not None:
        meta["source_category_id"] = source_category_id
    if form_dependencies is not None:
        meta["form_dependencies"] = [
            {
                "source_id": item.source_id,
                "target_id": item.target_id,
                "action": item.action,
            }
            for item in form_dependencies
        ]
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_instance_id,
            method="CONTENT",
            path=f"/api/content/admin/categories/{category_id}",
            status_code=200,
            meta=meta,
        )
    )


@router.get(
    "/categories",
    response_model=list[PublishedCategorySummaryResponse],
    dependencies=[Depends(enforce_user_access_available)],
)
def list_published_categories(
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[PublishedCategorySummaryResponse]:
    items = ListPublishedContent(SqlAlchemyContentRepository(db)).execute(_bot_id(bot))
    return [_published_summary(item) for item in items]


@router.get(
    "/catalog",
    response_model=list[PublishedContentResponse],
    dependencies=[Depends(enforce_user_access_available)],
)
def get_published_catalog(
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> list[PublishedContentResponse]:
    """Return every published page needed to render the tenant mini-app."""

    items = ListPublishedContent(SqlAlchemyContentRepository(db)).execute(_bot_id(bot))
    return [_published_response(item, db) for item in items]


@router.get(
    "/categories/home",
    response_model=PublishedContentResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def get_published_home_category(
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> PublishedContentResponse:
    """Registered before `/categories/{slug}` -- otherwise that route would swallow "home" as a
    literal slug lookup instead of reaching this handler."""
    repository = SqlAlchemyContentRepository(db)
    bot_id = _bot_id(bot)
    category, _ = GetOrCreateHomeCategory(repository).execute(bot_id, bot.name)
    db.commit()
    assert category.id is not None
    content = repository.get_published_by_category(bot_id, category.id)
    if content is None:
        raise not_found("Home screen not published", code="content_not_found")
    return _published_response(content, db)


@router.get(
    "/categories/{slug}",
    response_model=PublishedContentResponse,
    dependencies=[Depends(enforce_user_access_available)],
)
def get_published_category(
    slug: str,
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> PublishedContentResponse:
    try:
        content = GetPublishedContent(SqlAlchemyContentRepository(db)).execute(_bot_id(bot), slug)
    except Exception as exc:
        _raise_content_error(exc)
    return _published_response(content, db)


@router.get("/admin/categories", response_model=list[AdminCategoryResponse])
def list_admin_categories(
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[AdminCategoryResponse]:
    repository = SqlAlchemyContentRepository(db)
    bot_id = _bot_id(context.bot)
    GetOrCreateHomeCategory(repository).execute(bot_id, context.bot.name)
    db.commit()
    items = ListContentCategories(repository).execute(bot_id)
    return [_admin_category_response(category, draft) for category, draft in items]


def _attachment_response(item: ContentAttachment) -> ContentAttachmentResponse:
    return ContentAttachmentResponse(
        id=item.id,
        name=item.name,
        mime=item.mime,
        size_bytes=item.size_bytes,
        url=make_signed_url(item.id, ttl_seconds=-1),
        created_at=item.created_at,
        referenced_by_draft=[
            ContentAttachmentReferenceResponse(category_id=ref.category_id, usage=ref.usage)
            for ref in item.referenced_by_draft
        ],
        referenced_by_published=[
            ContentAttachmentReferenceResponse(category_id=ref.category_id, usage=ref.usage)
            for ref in item.referenced_by_published
        ],
    )


@router.get("/admin/attachments", response_model=ContentAttachmentListResponse)
def list_admin_content_attachments(
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mime: str | None = Query(default=None, pattern=r"^(image|other)$"),
    q: str | None = Query(default=None, max_length=200),
) -> ContentAttachmentListResponse:
    page = ListContentAttachments(SqlAlchemyContentAssetCatalog(db)).execute(
        _bot_id(context.bot),
        limit=limit,
        offset=offset,
        mime_family=mime,
        search=q,
    )
    return ContentAttachmentListResponse(
        items=[_attachment_response(item) for item in page.items],
        total=page.total,
    )


@router.delete("/admin/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_content_attachment(
    attachment_id: int,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> Response:
    bot_id = _bot_id(context.bot)
    try:
        deleted = DeleteContentAttachment(SqlAlchemyContentAssetCatalog(db)).execute(bot_id, attachment_id)
        db.add(
            AuditLog(
                admin_id=context.principal.admin_id,
                bot_instance_id=bot_id,
                method="DELETE",
                path=f"/api/content/admin/attachments/{attachment_id}",
                status_code=204,
                meta={
                    "action": "content_attachment_deleted",
                    "attachment_id": deleted.id,
                    "bot_instance_id": bot_id,
                    "name": deleted.name,
                    "mime": deleted.mime,
                    "size_bytes": deleted.size_bytes,
                },
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc, ContentAttachmentNotFound):
            raise not_found("Файл не найден", code="content_attachment_not_found") from exc
        if isinstance(exc, ContentAttachmentInUse):
            raise conflict(
                "Файл используется в опубликованной версии контента",
                code="content_attachment_in_use",
                category_ids=exc.category_ids,
            ) from exc
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/forms", response_model=list[ContentFormOptionResponse])
def list_admin_content_forms(
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[ContentFormOptionResponse]:
    items = ListContentForms(SqlAlchemyContentAssetCatalog(db)).execute(
        _bot_id(context.bot)
    )
    return [ContentFormOptionResponse(id=item.id, name=item.name) for item in items]


@router.get("/admin/tests", response_model=list[ContentTestOptionResponse])
def list_admin_content_tests(
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[ContentTestOptionResponse]:
    items = ListContentTests(SqlAlchemyContentAssetCatalog(db)).execute(
        _bot_id(context.bot)
    )
    return [ContentTestOptionResponse(id=item.id, name=item.name) for item in items]


@router.get("/admin/shared-drafts", response_model=list[SharedContentDraftResponse])
def list_shared_content_drafts(
    _: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[SharedContentDraftResponse]:
    items = ListSharedContentDrafts(SqlAlchemyContentRepository(db)).execute()
    return [
        SharedContentDraftResponse(
            source_category_id=item.category.id,
            source_bot_instance_id=item.source_bot_instance_id,
            source_bot_name=item.source_bot_name,
            slug=item.category.slug,
            title=item.draft.title,
            subtitle=item.draft.subtitle,
            icon=item.category.icon,
            language=item.draft.language,
        )
        for item in items
        if item.category.id is not None
    ]


def _dependency_response(
    report: SharedContentDependencyReport,
    *,
    can_copy_forms: bool,
) -> SharedContentDependenciesResponse:
    return SharedContentDependenciesResponse(
        dependencies=[
            SharedContentFormDependencyResponse(
                source_id=item.source_id,
                source_slug=item.source_slug,
                label=item.label,
                status=item.status,
                can_copy=item.source_is_shared and can_copy_forms,
                matched_target_id=item.matched_target_id,
                matched_target_ready=item.matched_target_ready,
            )
            for item in report.form_dependencies
        ],
        targets=[
            FormDependencyTargetResponse(id=item.id, slug=item.slug, label=item.label)
            for item in report.form_targets
        ],
        blockers=[
            ContentDependencyBlockerResponse(
                kind=item.kind,
                code=item.code,
                count=item.count,
            )
            for item in report.blockers
        ],
    )


@router.get(
    "/admin/shared-drafts/{source_category_id}/dependencies",
    response_model=SharedContentDependenciesResponse,
)
def get_shared_content_dependencies(
    source_category_id: int,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> SharedContentDependenciesResponse:
    try:
        report = GetSharedContentDependencies(
            SqlAlchemyContentRepository(db),
            build_form_content_template_dependency_gateway(db),
        ).execute(
            bot_instance_id=_bot_id(context.bot),
            source_category_id=source_category_id,
        )
    except Exception as exc:
        _raise_content_error(exc)
    return _dependency_response(
        report,
        can_copy_forms=can_manage_form_dependencies(context, db),
    )


@router.post(
    "/admin/shared-drafts/{source_category_id}/import",
    response_model=SharedContentDraftImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_shared_content_draft(
    source_category_id: int,
    payload: SharedContentDraftImportRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> SharedContentDraftImportResponse:
    repository = SqlAlchemyContentRepository(db)
    try:
        result = ImportSharedContentDraft(
            repository,
            SqlAlchemyContentReferenceGateway(db),
            build_form_content_template_dependency_gateway(db),
        ).execute(
            ImportSharedContentDraftCommand(
                bot_instance_id=_bot_id(context.bot),
                source_category_id=source_category_id,
                slug=payload.slug,
                parent_id=payload.parent_id,
                order=payload.order,
                created_by=context.principal.admin_id,
                form_resolutions=tuple(
                    FormDependencyResolution(
                        source_id=item.source_id,
                        action=item.action,
                        target_id=getattr(item, "target_id", None),
                    )
                    for item in payload.resolutions
                ),
                can_copy_forms=can_manage_form_dependencies(context, db),
            )
        )
        assert result.category.id is not None
        _add_content_audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            category_id=result.category.id,
            source_category_id=source_category_id,
            action="shared_content_draft_imported",
            form_dependencies=result.form_dependencies,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return SharedContentDraftImportResponse(
        category=_admin_category_response(result.category, result.draft),
        dependencies=[
            ResolvedFormDependencyResponse(
                source_id=item.source_id,
                target_id=item.target_id,
                action=item.action,
                target_ready=item.target_ready,
            )
            for item in result.form_dependencies
        ],
    )


@router.post(
    "/admin/categories",
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_category(
    payload: CategoryCreateRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> AdminCategoryResponse:
    try:
        category, draft = CreateContentCategory(
            SqlAlchemyContentRepository(db),
            SqlAlchemyContentReferenceGateway(db),
        ).execute(
            CreateCategoryCommand(
                bot_instance_id=_bot_id(context.bot),
                created_by=context.principal.admin_id,
                **payload.model_dump(),
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return _admin_category_response(category, draft)


@router.patch("/admin/categories/{category_id}", response_model=AdminCategoryResponse)
def patch_admin_category(
    category_id: int,
    payload: CategoryPatchRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> AdminCategoryResponse:
    repository = SqlAlchemyContentRepository(db)
    try:
        category = UpdateContentCategory(repository).execute(
            UpdateCategoryCommand(
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                change_parent="parent_id" in payload.model_fields_set,
                change_subtitle="subtitle" in payload.model_fields_set,
                change_image="image_url" in payload.model_fields_set,
                **payload.model_dump(exclude_unset=True),
            )
        )
        # A capability shortcut has no draft to fetch.
        draft = (
            None
            if category.is_shortcut
            else GetContentDraft(repository).execute(_bot_id(context.bot), category_id)
        )
        if payload.is_active is not None:
            _add_content_audit(
                db,
                admin_id=context.principal.admin_id,
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                action="category_activated" if payload.is_active else "category_archived",
            )
        elif "parent_id" in payload.model_fields_set:
            _add_content_audit(
                db,
                admin_id=context.principal.admin_id,
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                action="category_parent_changed",
            )
        elif payload.icon is not None:
            _add_content_audit(
                db,
                admin_id=context.principal.admin_id,
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                action="category_icon_changed",
            )
        elif (
            payload.title is not None
            or "subtitle" in payload.model_fields_set
            or "image_url" in payload.model_fields_set
        ):
            _add_content_audit(
                db,
                admin_id=context.principal.admin_id,
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                action="category_shortcut_card_changed",
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return _admin_category_response(category, draft)


@router.get("/admin/categories/{category_id}/draft", response_model=DraftResponse)
def get_admin_draft(
    category_id: int,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> DraftResponse:
    try:
        draft = GetContentDraft(SqlAlchemyContentRepository(db)).execute(_bot_id(context.bot), category_id)
    except Exception as exc:
        _raise_content_error(exc)
    return _draft_response(draft)


@router.put("/admin/categories/{category_id}/draft", response_model=DraftResponse)
def save_admin_draft(
    category_id: int,
    payload: DraftSaveRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> DraftResponse:
    repository = SqlAlchemyContentRepository(db)
    try:
        draft = SaveContentDraft(
            repository,
            SqlAlchemyContentReferenceGateway(db),
        ).execute(
            SaveDraftCommand(
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                updated_by=context.principal.admin_id,
                **payload.model_dump(mode="json"),
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return _draft_response(draft)


@router.post(
    "/admin/categories/{category_id}/preview-token",
    response_model=PreviewTokenResponse,
)
def issue_content_preview_token(
    category_id: int,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> PreviewTokenResponse:
    """Mint a short-lived, self-contained token the mini-app resolves with no admin session."""
    bot_id = _bot_id(context.bot)
    if SqlAlchemyContentRepository(db).get_category(bot_id, category_id) is None:
        raise not_found("Content category not found", code="content_not_found")
    token, expires_at = make_preview_token(bot_instance_id=bot_id, category_id=category_id)
    return PreviewTokenResponse(
        token=token,
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
    )


@router.get("/preview/{token}", response_model=DraftPreviewResponse)
def resolve_content_preview(token: str, db: Session = Depends(get_db)) -> DraftPreviewResponse:
    """Public, token-gated: lets the mini-app render an unpublished draft with no admin session."""
    try:
        payload = verify_preview_token(token)
    except InvalidPreviewToken as exc:
        raise bad_request(str(exc), code="invalid_preview_token") from exc
    bot_instance_id, category_id = payload.bot_instance_id, payload.category_id

    bot_slug = get_available_bot_slug(db, bot_instance_id)
    if bot_slug is None:
        raise not_found("Bot instance not found", code="bot_not_found")

    repository = SqlAlchemyContentRepository(db)
    category = repository.get_category(bot_instance_id, category_id)
    if category is None:
        raise not_found("Content category not found", code="content_not_found")
    try:
        draft = GetContentDraft(repository).execute(bot_instance_id, category_id)
    except ContentNotFound as exc:
        raise not_found("Draft not found", code="content_not_found") from exc

    assert category.id is not None
    _, attachment_ids = extract_references(draft.blocks)
    content = PublishedContentResponse(
        id=category.id,
        slug=category.slug,
        parent_id=category.parent_id,
        icon=category.icon,
        order=category.order,
        title=draft.title,
        subtitle=draft.subtitle,
        version_id=0,
        version=draft.revision,
        is_filled=draft.is_filled,
        image_url=draft.image_url,
        header_visible=draft.header_visible,
        is_home=category.is_home,
        capability_key=None,
        capability_view_key=None,
        language=draft.language,
        blocks=draft.blocks,
        attachment_urls=_attachment_urls(db, bot_instance_id=bot_instance_id, attachment_ids=attachment_ids),
        published_at=datetime.now(tz=timezone.utc),
    )
    # Both the JWT lifetime and the reported expiry come from the token's own remaining TTL,
    # not a fresh full window -- otherwise a token resolved just before expiry would hand out
    # another full DEFAULT_PREVIEW_TTL_SECONDS of access.
    expires_at = datetime.fromtimestamp(payload.expires_at, tz=timezone.utc)
    remaining_seconds = max(1, payload.expires_at - int(datetime.now(tz=timezone.utc).timestamp()))
    preview_access_token = create_access_token(
        {
            "sub": "preview",
            "role": "student",
            "system": "max",
            "bot_instance_id": bot_instance_id,
        },
        expires_min=max(1, remaining_seconds // 60),
    )
    return DraftPreviewResponse(
        content=content,
        preview_access_token=preview_access_token,
        bot_slug=bot_slug,
        expires_at=expires_at,
    )


@router.post(
    "/admin/categories/{category_id}/publish",
    response_model=PublishedContentResponse,
)
def publish_admin_category(
    category_id: int,
    payload: PublishRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> PublishedContentResponse:
    try:
        content = PublishContent(
            SqlAlchemyContentRepository(db),
            SqlAlchemyContentReferenceGateway(db),
        ).execute(
            PublishContentCommand(
                bot_instance_id=_bot_id(context.bot),
                category_id=category_id,
                expected_revision=payload.expected_revision,
                published_by=context.principal.admin_id,
            )
        )
        _add_content_audit(
            db,
            admin_id=context.principal.admin_id,
            bot_instance_id=_bot_id(context.bot),
            category_id=category_id,
            action="content_published",
            version_id=content.version.id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return _published_response(content, db)


@router.post("/admin/categories/reorder", response_model=list[AdminCategoryResponse])
def reorder_admin_categories(
    payload: ReorderRequest,
    context: ContentManagerContext = Depends(require_content_manager),
    db: Session = Depends(get_db),
) -> list[AdminCategoryResponse]:
    repository = SqlAlchemyContentRepository(db)
    bot_instance_id = _bot_id(context.bot)
    try:
        ReorderContentCategories(repository).execute(bot_instance_id, payload.category_ids)
        items = ListContentCategories(repository).execute(bot_instance_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return [_admin_category_response(category, draft) for category, draft in items]


@router.post("/events/category-open", status_code=status.HTTP_204_NO_CONTENT)
def record_category_open(
    payload: ContentOpenEventRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> Response:
    try:
        RecordContentCategoryOpen(
            SqlAlchemyContentRepository(db),
            SqlAlchemyContentAnalyticsGateway(db),
        ).execute(
            bot_instance_id=_bot_id(bot),
            user_id=principal.user_id,
            category_id=payload.category_id,
            version_id=payload.version_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/events/tab-open", status_code=status.HTTP_204_NO_CONTENT)
def record_tab_open(
    payload: ContentTabOpenEventRequest,
    principal: CurrentPrincipal = Depends(require_student),
    bot: BotInstance = Depends(require_tenant_access),
    db: Session = Depends(get_db),
) -> Response:
    try:
        RecordContentTabOpen(
            SqlAlchemyContentRepository(db),
            SqlAlchemyContentAnalyticsGateway(db),
        ).execute(
            bot_instance_id=_bot_id(bot),
            user_id=principal.user_id,
            category_id=payload.category_id,
            version_id=payload.version_id,
            tab_key=payload.tab_key,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_content_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
