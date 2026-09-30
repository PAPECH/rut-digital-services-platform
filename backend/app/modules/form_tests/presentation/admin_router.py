from __future__ import annotations

from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....core.errors import bad_request, conflict, not_found
from ....db.session import get_db
from ....modules.audit.infrastructure.models import AuditLog
from ...profiles.infrastructure.models import User
from ..application.commands import (
    CreateConsentDocumentCommand,
    CreateTestCommand,
    PreviewTestResultCommand,
    PublishTestCommand,
    SaveTestDraftCommand,
    UpdateConsentDocumentCommand,
    UpdateTestCommand,
)
from ..application.use_cases import (
    AttemptNotFound,
    ConsentCheckboxTextRequired,
    ConsentDocumentNotFound,
    CreateConsentDocument,
    CreateTest,
    DeleteConsentDocument,
    GetAttemptDetailAdmin,
    GetConsentDocument,
    GetTestDetailAdmin,
    GetTestDraft,
    ListAttemptsAdmin,
    ListConsentDocuments,
    ListTestsAdmin,
    NothingToPublish,
    PreviewTestResult,
    PublishTest,
    ReorderTests,
    SaveTestDraft,
    TestDraftRevisionConflict,
    TestNotAvailable,
    TestNotFound,
    TestSlugExists,
    UpdateConsentDocument,
    UpdateTest,
)
from ..domain.entities import (
    ConsentDocument,
    PublishedTest,
    TestAttempt,
    TestAttemptStatus,
    TestDefinition,
    TestDraft,
)
from ..domain.errors import TestSchemaValidationError
from ..infrastructure.repositories import SqlAlchemyTestRepository
from ..infrastructure.xlsx_export import build_attempts_workbook
from ..infrastructure.xlsx_schema import XlsxSchemaError, read_schema_workbook, write_schema_workbook
from .dependencies import TestManagerContext, require_test_manager
from .schemas import (
    AdminAttemptDetail,
    AdminAttemptSummary,
    AdminConsentDocumentDetail,
    AdminConsentDocumentSummary,
    AdminTestDetail,
    AdminTestSummary,
    AttemptSubmitterOut,
    ConsentDocumentContentOut,
    ConsentDocumentSaveRequest,
    TestCreateRequest,
    TestDraftResponse,
    TestDraftSaveRequest,
    TestPreviewRequest,
    TestPreviewResponse,
    TestPublishRequest,
    TestReorderRequest,
    TestSchemaExportResponse,
    UpdateTestRequest,
)

router = APIRouter(dependencies=[Depends(require_test_manager)])

MAX_IMPORT_FILE_BYTES = 10 * 1024 * 1024


def _summary(definition: TestDefinition) -> AdminTestSummary:
    assert definition.id is not None
    return AdminTestSummary(
        id=definition.id,
        slug=definition.slug,
        name=definition.name,
        order=definition.order,
        is_active=definition.is_active,
        is_archived=definition.is_archived,
        published_version_id=definition.published_version_id,
        last_published_revision=definition.last_published_revision,
    )


def _detail(published: PublishedTest) -> AdminTestDetail:
    base = _summary(published.definition)
    return AdminTestDetail(
        **base.model_dump(),
        intro_text=published.version.intro_text,
        test_schema=published.version.schema,
        consent_enabled=published.version.consent_enabled,
        consent_document_title=published.version.consent_document_title,
        consent_checkbox_text=published.version.consent_checkbox_text,
        allow_retake=published.version.allow_retake,
        show_attempt_history=published.version.show_attempt_history,
        show_scores=published.version.show_scores,
    )


def _submitter_out(user: User) -> AttemptSubmitterOut:
    return AttemptSubmitterOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        patronymic=user.patronymic,
        username=user.username,
        photo_url=user.photo_url,
    )


def _load_submitters(db: Session, attempts: list[TestAttempt]) -> dict[int, AttemptSubmitterOut]:
    """One batched query for every distinct `user_id` in `attempts` -- avoids an N+1 query per
    row in the attempts list endpoint (Task 077)."""
    user_ids = {attempt.user_id for attempt in attempts}
    if not user_ids:
        return {}
    users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
    return {user.id: _submitter_out(user) for user in users}


def _load_identity_fallback(db: Session, attempts: list[TestAttempt]) -> dict[int, dict[str, object]]:
    """Task 080: a live-profile fallback for the `.xlsx` export's identity columns, needed only
    for an attempt completed before this shipped (no frozen `identity_snapshot` of its own). One
    batched query, mirroring `_load_submitters`' own N+1 avoidance immediately below."""
    user_ids = {attempt.user_id for attempt in attempts if not attempt.identity_snapshot}
    if not user_ids:
        return {}
    users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
    return {
        user.id: {
            "last_name": user.last_name,
            "first_name": user.first_name,
            "patronymic": user.patronymic,
            "birth_date": user.birth_date,
            "email": user.email,
        }
        for user in users
    }


def _attempt_summary(attempt: TestAttempt, submitter: AttemptSubmitterOut | None) -> AdminAttemptSummary:
    assert attempt.id is not None
    return AdminAttemptSummary(
        id=attempt.id,
        user_id=attempt.user_id,
        submitter=submitter,
        answers=attempt.answers,
        computed_results=attempt.computed_results,
        status=attempt.status.value,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        consent_accepted=attempt.consent_accepted,
        consent_accepted_at=attempt.consent_accepted_at,
    )


def _attempt_detail(attempt: TestAttempt, submitter: AttemptSubmitterOut | None) -> AdminAttemptDetail:
    base = _attempt_summary(attempt, submitter)
    return AdminAttemptDetail(
        **base.model_dump(),
        rendered_result_text=attempt.rendered_result_text,
    )


def _draft_response(draft: TestDraft, consent_document: ConsentDocument | None) -> TestDraftResponse:
    return TestDraftResponse(
        test_id=draft.test_definition_id,
        name=draft.name,
        intro_text=draft.intro_text,
        test_schema=draft.schema,
        revision=draft.revision,
        updated_at=draft.updated_at,
        consent_enabled=draft.consent_enabled,
        consent_document_id=draft.consent_document_id,
        consent_document_title=consent_document.title if consent_document else None,
        consent_document_missing=draft.consent_document_id is not None and consent_document is None,
        consent_checkbox_text=draft.consent_checkbox_text,
        allow_retake=draft.allow_retake,
        show_attempt_history=draft.show_attempt_history,
        show_scores=draft.show_scores,
    )


def _consent_document_summary(document: ConsentDocument) -> AdminConsentDocumentSummary:
    assert document.id is not None
    return AdminConsentDocumentSummary(id=document.id, title=document.title, updated_at=document.updated_at)


def _consent_document_detail(document: ConsentDocument) -> AdminConsentDocumentDetail:
    base = _consent_document_summary(document)
    return AdminConsentDocumentDetail(
        **base.model_dump(), body_html=document.body_html, created_at=document.created_at
    )


def _export_response(*, name: str, intro_text: str | None, schema: dict) -> TestSchemaExportResponse:
    return TestSchemaExportResponse(name=name, intro_text=intro_text, test_schema=schema)


def _audit_test(
    db: Session,
    *,
    admin_id: int | None,
    bot_instance_id: int,
    test_id: int | None,
    action: str,
    revision: int | None = None,
    version_id: int | None = None,
    test_ids: list[int] | None = None,
) -> None:
    path = f"/api/form-tests/admin/{test_id}" if test_id is not None else "/api/form-tests/admin/reorder"
    meta: dict[str, object] = {"action": action, "bot_instance_id": bot_instance_id, "revision": revision}
    if test_id is not None:
        meta["test_id"] = test_id
    if version_id is not None:
        meta["version_id"] = version_id
    if test_ids is not None:
        meta["test_ids"] = test_ids
    db.add(
        AuditLog(
            admin_id=admin_id,
            bot_instance_id=bot_instance_id,
            method="TEST",
            path=path,
            status_code=200,
            meta=meta,
        )
    )


def _raise_admin_test_error(exc: Exception) -> None:
    if isinstance(exc, TestNotFound):
        raise not_found("Test not found", code="test_not_found") from exc
    if isinstance(exc, TestNotAvailable):
        raise conflict(str(exc), code="test_not_available") from exc
    if isinstance(exc, AttemptNotFound):
        raise not_found("Attempt not found", code="attempt_not_found") from exc
    if isinstance(exc, TestSlugExists):
        raise conflict("Test slug already exists", code="test_slug_exists") from exc
    if isinstance(exc, TestDraftRevisionConflict):
        raise conflict("Draft was changed by another editor", code="test_draft_revision_conflict") from exc
    if isinstance(exc, NothingToPublish):
        raise conflict("Draft has no unpublished changes", code="nothing_to_publish") from exc
    if isinstance(exc, TestSchemaValidationError):
        raise bad_request(str(exc), code="invalid_test_schema", path=exc.path) from exc
    if isinstance(exc, ConsentDocumentNotFound):
        raise bad_request("Consent document not found", code="consent_document_not_found") from exc
    if isinstance(exc, ConsentCheckboxTextRequired):
        raise bad_request(
            "Consent checkbox text must reference the document link", code="consent_checkbox_text_required"
        ) from exc
    if isinstance(exc, ValueError):
        raise bad_request(str(exc), code="invalid_test") from exc
    raise exc


@router.get("", response_model=list[AdminTestSummary])
def list_tests(
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> list[AdminTestSummary]:
    definitions = ListTestsAdmin(SqlAlchemyTestRepository(db)).execute(ctx.bot.id)
    return [_summary(d) for d in definitions]


# Registered before the /{test_id} routes below, for the same reason as the /attempts/export.xlsx
# comment further down: "consent-documents" would otherwise be swallowed by /{test_id}'s string
# path segment before FastAPI ever gets to validate it as an int.
@router.get("/consent-documents", response_model=list[AdminConsentDocumentSummary])
def list_consent_documents(
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> list[AdminConsentDocumentSummary]:
    documents = ListConsentDocuments(SqlAlchemyTestRepository(db)).execute(ctx.bot.id)
    return [_consent_document_summary(d) for d in documents]


@router.post("/consent-documents", response_model=AdminConsentDocumentDetail, status_code=status.HTTP_201_CREATED)
def create_consent_document(
    payload: ConsentDocumentSaveRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminConsentDocumentDetail:
    try:
        document = CreateConsentDocument(SqlAlchemyTestRepository(db)).execute(
            CreateConsentDocumentCommand(
                bot_instance_id=ctx.bot.id,
                title=payload.title,
                body_html=payload.body_html,
                created_by=ctx.principal.admin_id,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return _consent_document_detail(document)


@router.get("/consent-documents/{document_id}", response_model=AdminConsentDocumentDetail)
def get_consent_document(
    document_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminConsentDocumentDetail:
    try:
        document = GetConsentDocument(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, document_id)
    except Exception as exc:
        _raise_admin_test_error(exc)
        raise
    return _consent_document_detail(document)


@router.put("/consent-documents/{document_id}", response_model=AdminConsentDocumentDetail)
def update_consent_document(
    document_id: int,
    payload: ConsentDocumentSaveRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminConsentDocumentDetail:
    try:
        document = UpdateConsentDocument(SqlAlchemyTestRepository(db)).execute(
            UpdateConsentDocumentCommand(
                bot_instance_id=ctx.bot.id,
                document_id=document_id,
                title=payload.title,
                body_html=payload.body_html,
                updated_by=ctx.principal.admin_id,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return _consent_document_detail(document)


@router.delete("/consent-documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consent_document(
    document_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> Response:
    try:
        DeleteConsentDocument(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, document_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{test_id}", response_model=AdminTestDetail)
def get_test_detail(
    test_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminTestDetail:
    try:
        published = GetTestDetailAdmin(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, test_id)
    except TestNotFound as exc:
        _raise_admin_test_error(exc)
        raise
    return _detail(published)


@router.patch("/{test_id}", response_model=AdminTestSummary)
def update_test(
    test_id: int,
    payload: UpdateTestRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminTestSummary:
    try:
        updated = UpdateTest(SqlAlchemyTestRepository(db)).execute(
            UpdateTestCommand(
                bot_instance_id=ctx.bot.id,
                test_id=test_id,
                is_active=payload.is_active,
                is_archived=payload.is_archived,
            )
        )
    except (TestNotFound, TestNotAvailable) as exc:
        _raise_admin_test_error(exc)
        raise
    db.commit()
    return _summary(updated)


@router.post("", response_model=AdminTestSummary, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestCreateRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminTestSummary:
    try:
        definition, draft = CreateTest(SqlAlchemyTestRepository(db)).execute(
            CreateTestCommand(
                bot_instance_id=ctx.bot.id,
                created_by=ctx.principal.admin_id,
                **payload.model_dump(),
            )
        )
        assert definition.id is not None
        _audit_test(
            db,
            admin_id=ctx.principal.admin_id,
            bot_instance_id=ctx.bot.id,
            test_id=definition.id,
            action="test_created",
            revision=draft.revision,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return _summary(definition)


@router.post("/reorder", response_model=list[AdminTestSummary])
def reorder_tests(
    payload: TestReorderRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> list[AdminTestSummary]:
    repository = SqlAlchemyTestRepository(db)
    try:
        definitions = ReorderTests(repository).execute(ctx.bot.id, payload.test_ids)
        _audit_test(
            db,
            admin_id=ctx.principal.admin_id,
            bot_instance_id=ctx.bot.id,
            test_id=None,
            test_ids=payload.test_ids,
            action="tests_reordered",
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return [_summary(d) for d in definitions]


@router.get("/{test_id}/draft", response_model=TestDraftResponse)
def get_test_draft(
    test_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> TestDraftResponse:
    repository = SqlAlchemyTestRepository(db)
    try:
        draft = GetTestDraft(repository).execute(ctx.bot.id, test_id)
    except Exception as exc:
        _raise_admin_test_error(exc)
        raise
    document = (
        repository.get_consent_document(ctx.bot.id, draft.consent_document_id)
        if draft.consent_document_id is not None
        else None
    )
    return _draft_response(draft, document)


@router.put("/{test_id}/draft", response_model=TestDraftResponse)
def save_test_draft(
    test_id: int,
    payload: TestDraftSaveRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> TestDraftResponse:
    repository = SqlAlchemyTestRepository(db)
    try:
        draft = SaveTestDraft(repository).execute(
            SaveTestDraftCommand(
                bot_instance_id=ctx.bot.id,
                test_id=test_id,
                expected_revision=payload.expected_revision,
                name=payload.name,
                intro_text=payload.intro_text,
                schema=payload.test_schema,
                updated_by=ctx.principal.admin_id,
                consent_enabled=payload.consent_enabled,
                consent_document_id=payload.consent_document_id,
                consent_checkbox_text=payload.consent_checkbox_text,
                allow_retake=payload.allow_retake,
                show_attempt_history=payload.show_attempt_history,
                show_scores=payload.show_scores,
            )
        )
        _audit_test(
            db,
            admin_id=ctx.principal.admin_id,
            bot_instance_id=ctx.bot.id,
            test_id=test_id,
            action="test_draft_saved",
            revision=draft.revision,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    document = (
        repository.get_consent_document(ctx.bot.id, draft.consent_document_id)
        if draft.consent_document_id is not None
        else None
    )
    return _draft_response(draft, document)


@router.post("/{test_id}/publish", response_model=AdminTestDetail)
def publish_test(
    test_id: int,
    payload: TestPublishRequest,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminTestDetail:
    try:
        published = PublishTest(SqlAlchemyTestRepository(db)).execute(
            PublishTestCommand(
                bot_instance_id=ctx.bot.id,
                test_id=test_id,
                expected_revision=payload.expected_revision,
                published_by=ctx.principal.admin_id,
            )
        )
        _audit_test(
            db,
            admin_id=ctx.principal.admin_id,
            bot_instance_id=ctx.bot.id,
            test_id=test_id,
            action="test_published",
            revision=published.version.source_revision,
            version_id=published.version.id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_admin_test_error(exc)
        raise
    return _detail(published)


@router.post("/{test_id}/preview", response_model=TestPreviewResponse)
def preview_test_result(
    test_id: int,  # unused: kept for URL symmetry with other per-test admin actions
    payload: TestPreviewRequest,
) -> TestPreviewResponse:
    try:
        rendered_text, chunks = PreviewTestResult().execute(
            PreviewTestResultCommand(
                filters=payload.filters,
                result_template=payload.result_template,
                sample_values=payload.sample_values,
            )
        )
    except Exception as exc:
        _raise_admin_test_error(exc)
        raise
    return TestPreviewResponse(rendered_text=rendered_text, chunks=chunks)


def _xlsx_response(workbook, filename: str) -> StreamingResponse:
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{test_id}/draft/export.xlsx")
def export_test_draft(
    test_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> StreamingResponse:
    try:
        draft = GetTestDraft(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, test_id)
    except Exception as exc:
        _raise_admin_test_error(exc)
        raise
    workbook = write_schema_workbook(name=draft.name, intro_text=draft.intro_text, schema=draft.schema)
    return _xlsx_response(workbook, f"test-{test_id}-draft.xlsx")


@router.get("/{test_id}/versions/{version_id}/export.xlsx")
def export_test_version(
    test_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> StreamingResponse:
    published = SqlAlchemyTestRepository(db).get_version(ctx.bot.id, test_id, version_id)
    if published is None:
        raise not_found("Test version not found", code="test_not_found")
    workbook = write_schema_workbook(
        name=published.version.name,
        intro_text=published.version.intro_text,
        schema=published.version.schema,
    )
    return _xlsx_response(workbook, f"test-{test_id}-version-{version_id}.xlsx")


@router.get("/{test_id}/versions/{version_id}/consent-document", response_model=ConsentDocumentContentOut)
def get_version_consent_document(
    test_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> ConsentDocumentContentOut:
    published = SqlAlchemyTestRepository(db).get_version(ctx.bot.id, test_id, version_id)
    if published is None:
        raise not_found("Test version not found", code="test_not_found")
    if not published.version.consent_enabled:
        raise not_found("This version has no participation consent configured", code="consent_not_enabled")
    return ConsentDocumentContentOut(
        title=published.version.consent_document_title or "",
        body_html=published.version.consent_document_body_html or "",
    )


@router.post("/{test_id}/draft/import.xlsx", response_model=TestSchemaExportResponse)
async def import_test_draft_xlsx(
    test_id: int,  # unused: kept for URL symmetry with other per-test admin actions; the parsed
    # content is returned for review, not written against a specific test until an ordinary
    # `PUT .../draft` follows -- see `xlsx_schema.read_schema_workbook`'s own docstring.
    file: UploadFile = File(...),
) -> TestSchemaExportResponse:
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise bad_request("Файл превышает лимит 10 МБ", code="file_too_large")
    try:
        parsed = read_schema_workbook(content)
    except XlsxSchemaError as exc:
        raise bad_request(str(exc), code="invalid_import_file") from exc
    return _export_response(
        name=parsed["name"], intro_text=parsed["intro_text"], schema=parsed["test_schema"]
    )


@router.get("/{test_id}/attempts", response_model=list[AdminAttemptSummary])
def list_attempts(
    test_id: int,
    status: TestAttemptStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> list[AdminAttemptSummary]:
    try:
        attempts = ListAttemptsAdmin(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, test_id, status=status)
    except TestNotFound as exc:
        _raise_admin_test_error(exc)
        raise
    submitters = _load_submitters(db, attempts)
    return [_attempt_summary(a, submitters.get(a.user_id)) for a in attempts]


# Registered before the /{attempt_id} route below: both match a 2-segment suffix after
# /attempts, and Starlette commits to whichever pattern was registered first regardless of
# specificity ("export.xlsx" is a syntactically valid, if later 422-rejected, value for
# {attempt_id}) -- the same class of collision fixed in api/router.py's own registration order.
@router.get("/{test_id}/attempts/export.xlsx")
def export_attempts_xlsx(
    test_id: int,
    value_mode: Literal["text", "score"] = Query(default="text"),
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> StreamingResponse:
    repository = SqlAlchemyTestRepository(db)
    try:
        published = GetTestDetailAdmin(repository).execute(ctx.bot.id, test_id)
    except TestNotFound as exc:
        _raise_admin_test_error(exc)
        raise
    attempts = ListAttemptsAdmin(repository).execute(ctx.bot.id, test_id, status=TestAttemptStatus.COMPLETED)
    fallback_identities = _load_identity_fallback(db, attempts)
    workbook = build_attempts_workbook(
        published.version.schema, attempts, value_mode=value_mode, fallback_identities=fallback_identities
    )
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"test-{test_id}-attempts.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{test_id}/attempts/{attempt_id}", response_model=AdminAttemptDetail)
def get_attempt_detail(
    test_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    ctx: TestManagerContext = Depends(require_test_manager),
) -> AdminAttemptDetail:
    try:
        attempt = GetAttemptDetailAdmin(SqlAlchemyTestRepository(db)).execute(ctx.bot.id, test_id, attempt_id)
    except AttemptNotFound as exc:
        _raise_admin_test_error(exc)
        raise
    user = db.get(User, attempt.user_id)
    return _attempt_detail(attempt, _submitter_out(user) if user else None)
