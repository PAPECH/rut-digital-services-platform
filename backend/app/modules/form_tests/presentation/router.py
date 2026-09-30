from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....api.deps import CurrentPrincipal, require_student
from ....core.errors import bad_request, conflict, forbidden, not_found
from ....db.session import get_db
from ...bot_instances.domain.entities import BotInstance
from ...maintenance.presentation.dependencies import (
    enforce_user_access_available,
    enforce_user_write_available,
)
from ...profiles.infrastructure.gateways import SqlAlchemyProfileGateway
from ...tenancy.presentation.dependencies import require_tenant_access
from ..application.commands import AutosaveAttemptCommand, CompleteAttemptCommand
from ..application.profile_requirements import find_missing_test_participation_fields
from ..application.use_cases import (
    AttemptAlreadyCompleted,
    AttemptForbidden,
    AttemptNotFound,
    AutosaveAttempt,
    CompleteAttempt,
    ConsentRequired,
    GetAttempt,
    GetPublishedTest,
    ListActiveTests,
    ListMyAttempts,
    RetakeAttempt,
    RetakeNotAllowed,
    StartOrResumeAttempt,
    TestNotAvailable,
    TestNotFound,
)
from ..domain.elements import TestAnswerValidationError
from ..domain.entities import PublishedTest, TestAttempt
from ..domain.errors import ResultScaleError
from ..infrastructure.push_delivery import PushResultDeliveryGateway
from ..infrastructure.repositories import SqlAlchemyTestRepository
from .schemas import (
    AttemptOut,
    AutosaveAttemptRequest,
    CompleteAttemptRequest,
    ConsentDocumentContentOut,
    PublishedTestDetail,
    PublishedTestSummary,
)

router = APIRouter(dependencies=[Depends(enforce_user_access_available)])


def _summary(published: PublishedTest) -> PublishedTestSummary:
    assert published.definition.id is not None and published.version.id is not None
    return PublishedTestSummary(
        id=published.definition.id,
        slug=published.definition.slug,
        name=published.version.name,
        version_id=published.version.id,
        version=published.version.version,
    )


def _detail(published: PublishedTest) -> PublishedTestDetail:
    assert published.definition.id is not None and published.version.id is not None
    return PublishedTestDetail.from_schema(
        id=published.definition.id,
        slug=published.definition.slug,
        name=published.version.name,
        intro_text=published.version.intro_text,
        version_id=published.version.id,
        version=published.version.version,
        elements=published.version.schema["elements"],
        consent_enabled=published.version.consent_enabled,
        consent_checkbox_text=published.version.consent_checkbox_text,
        consent_document_title=published.version.consent_document_title,
        allow_retake=published.version.allow_retake,
        show_scores=published.version.show_scores,
        result_scales=published.version.schema.get("result_scales"),
    )


def _attempt_out(attempt: TestAttempt, *, show_scores: bool) -> AttemptOut:
    """`show_scores` is this module's one place that redacts `computed_results` for a student's
    own read (Task 075) -- the domain/use-case/repository layers behind `attempt` always stay
    truthful (see `test_form_tests_use_cases.py`'s use-case-layer coverage); this is the API
    boundary, the same role `_student_safe_elements` already plays for option scores."""
    assert attempt.id is not None
    return AttemptOut(
        id=attempt.id,
        test_definition_id=attempt.test_definition_id,
        test_version_id=attempt.test_version_id,
        status=attempt.status.value,
        answers=attempt.answers,
        computed_results=attempt.computed_results if show_scores else None,
        rendered_result_text=attempt.rendered_result_text,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        consent_accepted=attempt.consent_accepted,
        consent_accepted_at=attempt.consent_accepted_at,
    )


def _show_scores_for(repository: SqlAlchemyTestRepository, bot_instance_id: int, attempt: TestAttempt) -> bool:
    if attempt.computed_results is None:
        return True  # nothing to redact -- avoids a needless lookup for in-progress attempts
    published = repository.get_version(bot_instance_id, attempt.test_definition_id, attempt.test_version_id)
    return published is not None and published.version.show_scores


def _raise_test_error(exc: Exception) -> None:
    if isinstance(exc, TestNotFound):
        raise not_found("Test not found", code="test_not_found") from exc
    if isinstance(exc, TestNotAvailable):
        raise not_found("Test is not available", code="test_not_available") from exc
    if isinstance(exc, AttemptNotFound):
        raise not_found("Attempt not found", code="attempt_not_found") from exc
    if isinstance(exc, AttemptForbidden):
        raise forbidden("Attempt belongs to another user", code="attempt_forbidden") from exc
    if isinstance(exc, AttemptAlreadyCompleted):
        raise conflict("Attempt is already completed", code="attempt_already_completed") from exc
    if isinstance(exc, ConsentRequired):
        raise bad_request(
            "Participation consent must be accepted before completing this test", code="consent_required"
        ) from exc
    if isinstance(exc, RetakeNotAllowed):
        raise conflict("Retake is not allowed for this test", code="retake_not_allowed") from exc
    if isinstance(exc, TestAnswerValidationError):
        raise bad_request(
            str(exc),
            code="invalid_test_answer" if exc.question_key else "missing_required_answer",
            question_key=exc.question_key,
        ) from exc
    if isinstance(exc, ResultScaleError):  # pragma: no cover - schema bug, not a user error
        raise bad_request(str(exc), code="invalid_test_schema") from exc


@router.get("", response_model=list[PublishedTestSummary])
def list_active_tests(
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
) -> list[PublishedTestSummary]:
    published = ListActiveTests(SqlAlchemyTestRepository(db)).execute(bot.id)
    return [_summary(p) for p in published]


@router.get("/attempts", response_model=list[AttemptOut])
def list_my_attempts(
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> list[AttemptOut]:
    repository = SqlAlchemyTestRepository(db)
    attempts = ListMyAttempts(repository).execute(bot.id, p.user_id)
    return [_attempt_out(a, show_scores=_show_scores_for(repository, bot.id, a)) for a in attempts]


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> AttemptOut:
    repository = SqlAlchemyTestRepository(db)
    try:
        attempt = GetAttempt(repository).execute(
            bot_instance_id=bot.id, user_id=p.user_id, attempt_id=attempt_id
        )
    except (AttemptNotFound, AttemptForbidden) as exc:
        _raise_test_error(exc)
        raise
    return _attempt_out(attempt, show_scores=_show_scores_for(repository, bot.id, attempt))


@router.get("/{test_id}", response_model=PublishedTestDetail)
def get_published_test(
    test_id: int,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
) -> PublishedTestDetail:
    try:
        published = GetPublishedTest(SqlAlchemyTestRepository(db)).execute(bot.id, test_id)
    except (TestNotFound, TestNotAvailable) as exc:
        _raise_test_error(exc)
        raise
    return _detail(published)


@router.get("/{test_id}/consent-document", response_model=ConsentDocumentContentOut)
def get_test_consent_document(
    test_id: int,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
) -> ConsentDocumentContentOut:
    try:
        published = GetPublishedTest(SqlAlchemyTestRepository(db)).execute(bot.id, test_id)
    except (TestNotFound, TestNotAvailable) as exc:
        _raise_test_error(exc)
        raise
    if not published.version.consent_enabled:
        raise not_found("This test has no participation consent configured", code="consent_not_enabled")
    return ConsentDocumentContentOut(
        title=published.version.consent_document_title or "",
        body_html=published.version.consent_document_body_html or "",
    )


def _require_participation_profile(db: Session, user_id: int) -> None:
    """`form_tests`-only gate (Task 080): a student's shared profile must have their name,
    verified phone (existing platform-wide rule), birth date, and email before they can start or
    resume an attempt -- the anketa no longer asks for these itself. Mirrors
    `modules.forms.presentation.submissions_router._get_complete_profile`'s exact shape
    (`profile_incomplete`, same error code) without touching that module or the shared
    `CORE_REQUIREMENTS` it relies on."""
    profile = SqlAlchemyProfileGateway(db).get_shared_profile(user_id)
    if profile is None:
        raise not_found("Профиль не найден")
    missing = find_missing_test_participation_fields(profile)
    if missing:
        raise bad_request(
            "Заполните профиль перед началом теста: " + ", ".join(missing),
            code="profile_incomplete",
        )


@router.post(
    "/{test_id}/attempts",
    response_model=AttemptOut,
    status_code=201,
    dependencies=[Depends(enforce_user_write_available)],
)
def start_or_resume_attempt(
    test_id: int,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> AttemptOut:
    _require_participation_profile(db, p.user_id)
    repository = SqlAlchemyTestRepository(db)
    try:
        attempt = StartOrResumeAttempt(repository).execute(
            bot_instance_id=bot.id, user_id=p.user_id, test_id=test_id
        )
    except (TestNotFound, TestNotAvailable) as exc:
        _raise_test_error(exc)
        raise
    db.commit()
    return _attempt_out(attempt, show_scores=_show_scores_for(repository, bot.id, attempt))


@router.post(
    "/{test_id}/attempts/retake",
    response_model=AttemptOut,
    status_code=201,
    dependencies=[Depends(enforce_user_write_available)],
)
def retake_attempt(
    test_id: int,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> AttemptOut:
    _require_participation_profile(db, p.user_id)
    try:
        attempt = RetakeAttempt(SqlAlchemyTestRepository(db)).execute(
            bot_instance_id=bot.id, user_id=p.user_id, test_id=test_id
        )
    except (TestNotFound, TestNotAvailable, RetakeNotAllowed) as exc:
        _raise_test_error(exc)
        raise
    db.commit()
    # A retake is always a brand-new or resumed in-progress attempt -- never has computed_results
    # yet, so there's nothing for `show_scores` to redact.
    return _attempt_out(attempt, show_scores=True)


@router.patch(
    "/attempts/{attempt_id}",
    response_model=AttemptOut,
    dependencies=[Depends(enforce_user_write_available)],
)
def autosave_attempt(
    attempt_id: int,
    payload: AutosaveAttemptRequest,
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> AttemptOut:
    try:
        attempt = AutosaveAttempt(SqlAlchemyTestRepository(db)).execute(
            AutosaveAttemptCommand(
                bot_instance_id=bot.id, user_id=p.user_id, attempt_id=attempt_id, answers=payload.answers
            )
        )
    except (AttemptNotFound, AttemptForbidden, AttemptAlreadyCompleted, TestAnswerValidationError) as exc:
        _raise_test_error(exc)
        raise
    db.commit()
    # An in-progress attempt never has computed_results yet -- nothing for `show_scores` to redact.
    return _attempt_out(attempt, show_scores=True)


@router.post(
    "/attempts/{attempt_id}/complete",
    response_model=AttemptOut,
    dependencies=[Depends(enforce_user_write_available)],
)
def complete_attempt(
    attempt_id: int,
    payload: CompleteAttemptRequest = CompleteAttemptRequest(),
    db: Session = Depends(get_db),
    bot: BotInstance = Depends(require_tenant_access),
    p: CurrentPrincipal = Depends(require_student),
) -> AttemptOut:
    repository = SqlAlchemyTestRepository(db)
    delivery = PushResultDeliveryGateway(db)
    try:
        attempt = CompleteAttempt(repository, delivery, SqlAlchemyProfileGateway(db)).execute(
            CompleteAttemptCommand(
                bot_instance_id=bot.id,
                user_id=p.user_id,
                attempt_id=attempt_id,
                consent_accepted=payload.consent_accepted,
            )
        )
    except (
        AttemptNotFound,
        AttemptForbidden,
        AttemptAlreadyCompleted,
        TestAnswerValidationError,
        ResultScaleError,
        ConsentRequired,
    ) as exc:
        _raise_test_error(exc)
        raise
    db.commit()
    return _attempt_out(attempt, show_scores=_show_scores_for(repository, bot.id, attempt))
