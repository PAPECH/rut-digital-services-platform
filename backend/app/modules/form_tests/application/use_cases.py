from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from ..domain.attempt_scoring import ScoredAttempt, score_attempt
from ..domain.consent import validate_consent_document_body, validate_consent_document_title
from ..domain.elements import validate_partial_answers
from ..domain.entities import (
    ConsentDocument,
    PublishedTest,
    TestAttempt,
    TestAttemptStatus,
    TestDefinition,
    TestDraft,
)
from ...profiles.domain.entities import SharedProfile
from ..domain.filters import match_all_filters, validate_filters
from ..domain.message_split import split_message
from ..domain.repositories import TestRepository
from ..domain.schema import validate_test_schema, validate_test_schema_draft
from ..domain.template import render_result_template, validate_template
from .commands import (
    AutosaveAttemptCommand,
    CompleteAttemptCommand,
    CreateConsentDocumentCommand,
    CreateTestCommand,
    PreviewTestResultCommand,
    PublishTestCommand,
    SaveTestDraftCommand,
    UpdateConsentDocumentCommand,
    UpdateTestCommand,
)
from .ports import ProfileReader, ResultDeliveryGateway

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
HTML_TAG_RE = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")

MAX_MESSAGE_LENGTH = 4000

_EMPTY_SCHEMA: dict[str, Any] = {
    "elements": [],
    "result_scales": [],
    "filters": [],
    "result_template": "",
}


class TestNotFound(RuntimeError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery


class TestNotAvailable(RuntimeError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery


class TestSlugExists(RuntimeError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery


class TestDraftRevisionConflict(RuntimeError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery


class NothingToPublish(RuntimeError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery


class AttemptNotFound(RuntimeError):
    pass


class AttemptForbidden(RuntimeError):
    pass


class AttemptAlreadyCompleted(RuntimeError):
    pass


class RetakeNotAllowed(RuntimeError):
    """Raised by `RetakeAttempt` (Task 075) when the current published version has
    `allow_retake=False`, or the caller has no completed attempt against it to retake from. An
    existing *in-progress* attempt is resumed instead of raising -- see `RetakeAttempt.execute`."""


class ConsentRequired(RuntimeError):
    """Raised by `CompleteAttempt` when the attempt's own published version has the
    participation-consent checkbox enabled and the completion request did not carry
    `consent_accepted: true` -- the server is the sole authority on whether consent was actually
    given, never inferred from the client (Task 073)."""


class ConsentDocumentNotFound(RuntimeError):
    """A `TestDraft`/`TestVersion`'s `consent_document_id` does not resolve to an existing,
    same-bot `ConsentDocument` -- raised at draft-save (a freshly submitted id that doesn't
    resolve) and at publish (a dangling id left over from a deleted document, or none picked while
    `consent_enabled` is true). Also raised by `GetConsentDocument`/`UpdateConsentDocument`/
    `DeleteConsentDocument` for a missing/cross-tenant document id."""


class ConsentCheckboxTextRequired(RuntimeError):
    """Publish-time-only: `consent_enabled` is true but the checkbox text is blank or does not
    contain the click-inserted document-link placeholder exactly once (Task 073)."""


def _require_available(published: PublishedTest) -> PublishedTest:
    if published.definition.is_archived or not published.definition.is_active:
        raise TestNotAvailable(published.definition.id)
    return published


class ListActiveTests:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[PublishedTest]:
        return self._repository.list_active_published(bot_instance_id)


class GetPublishedTest:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, test_id: int) -> PublishedTest:
        published = self._repository.get_published(bot_instance_id, test_id)
        if published is None:
            raise TestNotFound(test_id)
        return _require_available(published)


class StartOrResumeAttempt:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, *, bot_instance_id: int, user_id: int, test_id: int) -> TestAttempt:
        published = GetPublishedTest(self._repository).execute(bot_instance_id, test_id)
        assert published.version.id is not None
        existing = self._repository.get_attempt_for_version(bot_instance_id, user_id, published.version.id)
        if existing is not None:
            # Reopening a completed test always returns the existing result (Task 075) --
            # regardless of `allow_retake`; retaking is a separate, explicit action (`RetakeAttempt`).
            return existing
        # No attempt exists yet for the currently published version -- but a republish between the
        # student's previous visit and this one (an admin editing/publishing in the constructor
        # while the student's attempt was still in progress) may have left an in-progress attempt
        # behind on the now-superseded version, orphaned since this method only ever looks at the
        # *current* version. Left alone it would sit forever as a duplicate "in progress" row in
        # the student's own history; discard it before starting the fresh attempt below.
        self._repository.delete_stale_in_progress_attempts(
            bot_instance_id, user_id, published.definition.id
        )
        return self._repository.create_attempt(
            bot_instance_id=bot_instance_id,
            test_definition_id=published.definition.id,
            test_version_id=published.version.id,
            user_id=user_id,
        )


class RetakeAttempt:
    """Explicit, student-initiated action (Task 075): starts a brand-new attempt against the
    current published version, independent of any prior one, when that version's own
    `allow_retake` is on. Never called implicitly by `StartOrResumeAttempt` -- reopening a
    completed test always shows the existing result first; retaking is a deliberate extra step."""

    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, *, bot_instance_id: int, user_id: int, test_id: int) -> TestAttempt:
        published = GetPublishedTest(self._repository).execute(bot_instance_id, test_id)
        assert published.version.id is not None
        if not published.version.allow_retake:
            raise RetakeNotAllowed(test_id)
        existing = self._repository.get_attempt_for_version(bot_instance_id, user_id, published.version.id)
        if existing is not None and existing.status == TestAttemptStatus.IN_PROGRESS:
            return existing
        if existing is None or existing.status != TestAttemptStatus.COMPLETED:
            raise RetakeNotAllowed(test_id)
        return self._repository.create_attempt(
            bot_instance_id=bot_instance_id,
            test_definition_id=published.definition.id,
            test_version_id=published.version.id,
            user_id=user_id,
        )


def _owned_in_progress_attempt(
    repository: TestRepository, *, bot_instance_id: int, user_id: int, attempt_id: int
) -> TestAttempt:
    attempt = repository.get_attempt(bot_instance_id, attempt_id)
    if attempt is None:
        raise AttemptNotFound(attempt_id)
    if attempt.user_id != user_id:
        raise AttemptForbidden(attempt_id)
    if attempt.status != TestAttemptStatus.IN_PROGRESS:
        raise AttemptAlreadyCompleted(attempt_id)
    return attempt


class AutosaveAttempt:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: AutosaveAttemptCommand) -> TestAttempt:
        attempt = _owned_in_progress_attempt(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            user_id=command.user_id,
            attempt_id=command.attempt_id,
        )
        published = self._repository.get_version(
            command.bot_instance_id, attempt.test_definition_id, attempt.test_version_id
        )
        assert published is not None
        normalized = validate_partial_answers(published.version.schema["elements"], command.answers)
        return self._repository.save_attempt_answers(command.attempt_id, normalized)


def _build_computed_results(schema: dict[str, Any], scored: ScoredAttempt) -> dict[str, Any]:
    aggregation_by_key = {scale["key"]: scale["aggregation"] for scale in schema["result_scales"]}
    return {
        key: {
            "value": value,
            "aggregation": aggregation_by_key[key],
            "filter": scored.matched_filters.get(key),
        }
        for key, value in scored.computed_values.items()
    }


_IDENTITY_SNAPSHOT_FIELDS = ("last_name", "first_name", "patronymic", "birth_date", "email")


def _identity_snapshot(profile: SharedProfile | None) -> dict[str, Any]:
    """Freezes the five identity fields the RUT SPT anketa no longer asks for itself (Task 080)
    onto the attempt at the moment it's completed -- a later profile edit must never change what
    an already-completed attempt reports, the same guarantee `rendered_result_text` and the
    consent document's frozen copy (Task 073) already give this module. `None` profile (should not
    happen in practice -- `StartOrResumeAttempt`'s own gate already required one -- but the type
    is optional defensively) freezes every field as `None` rather than failing completion."""
    if profile is None:
        return dict.fromkeys(_IDENTITY_SNAPSHOT_FIELDS)
    return {
        "last_name": profile.last_name,
        "first_name": profile.first_name,
        "patronymic": profile.patronymic,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "email": profile.email,
    }


class CompleteAttempt:
    def __init__(
        self,
        repository: TestRepository,
        delivery: ResultDeliveryGateway,
        profiles: ProfileReader | None = None,
    ) -> None:
        self._repository = repository
        self._delivery = delivery
        self._profiles = profiles

    def execute(self, command: CompleteAttemptCommand) -> TestAttempt:
        attempt = _owned_in_progress_attempt(
            self._repository,
            bot_instance_id=command.bot_instance_id,
            user_id=command.user_id,
            attempt_id=command.attempt_id,
        )
        published = self._repository.get_version(
            command.bot_instance_id, attempt.test_definition_id, attempt.test_version_id
        )
        assert published is not None
        if published.version.consent_enabled and not command.consent_accepted:
            raise ConsentRequired(command.attempt_id)
        scored = score_attempt(published.version.schema, attempt.answers)
        profile = self._profiles.get_shared_profile(command.user_id) if self._profiles else None
        completed = self._repository.complete_attempt(
            command.attempt_id,
            answers=scored.answers,
            computed_results=_build_computed_results(published.version.schema, scored),
            rendered_result_text=scored.rendered_result_text,
            consent_accepted=published.version.consent_enabled and command.consent_accepted,
            identity_snapshot=_identity_snapshot(profile),
        )
        self._delivery.deliver_result(
            bot_instance_id=command.bot_instance_id,
            user_id=command.user_id,
            text=scored.rendered_result_text,
        )
        # `show_scores` never touches this use case's return value or the delivered chat message
        # above (which renders whatever the admin's own result template already chose to include,
        # Task 075 scope boundary) -- the domain/use-case layer always stays truthful. Redaction
        # for a student's own read happens only at the presentation layer (`_attempt_out`), the
        # same place `_student_safe_elements` already strips scoring internals before they reach
        # the client. An admin's own read of `computed_results` is never affected either way.
        return completed


class GetAttempt:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, *, bot_instance_id: int, user_id: int, attempt_id: int) -> TestAttempt:
        attempt = self._repository.get_attempt(bot_instance_id, attempt_id)
        if attempt is None:
            raise AttemptNotFound(attempt_id)
        if attempt.user_id != user_id:
            raise AttemptForbidden(attempt_id)
        return attempt


class ListMyAttempts:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, user_id: int) -> list[TestAttempt]:
        return self._repository.list_attempts_for_user(bot_instance_id, user_id)


# --- Admin (read-only + lifecycle toggle only -- see Task 068 Non-goals) --------------------


class ListTestsAdmin:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[TestDefinition]:
        return self._repository.list_tests(bot_instance_id)


class GetTestDetailAdmin:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, test_id: int) -> PublishedTest:
        published = self._repository.get_published(bot_instance_id, test_id)
        if published is None:
            raise TestNotFound(test_id)
        return published


class UpdateTest:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateTestCommand) -> TestDefinition:
        definition = self._repository.get_test(command.bot_instance_id, command.test_id)
        if definition is None:
            raise TestNotFound(command.test_id)
        updated = replace(
            definition,
            is_active=command.is_active if command.is_active is not None else definition.is_active,
            is_archived=command.is_archived if command.is_archived is not None else definition.is_archived,
        )
        if updated.is_archived:
            updated = replace(updated, is_active=False)
        if updated.is_active and updated.published_version_id is None:
            raise TestNotAvailable("Cannot activate a test with no published version")
        return self._repository.update_test(updated)


class ListAttemptsAdmin:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(
        self, bot_instance_id: int, test_id: int, *, status: TestAttemptStatus | None = None
    ) -> list[TestAttempt]:
        if self._repository.get_test(bot_instance_id, test_id) is None:
            raise TestNotFound(test_id)
        return self._repository.list_attempts_for_test(bot_instance_id, test_id, status=status)


class GetAttemptDetailAdmin:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, test_id: int, attempt_id: int) -> TestAttempt:
        attempt = self._repository.get_attempt(bot_instance_id, attempt_id)
        if attempt is None or attempt.test_definition_id != test_id:
            raise AttemptNotFound(attempt_id)
        return attempt


# --- Admin constructor (Task 069) -----------------------------------------------------------


class CreateTest:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateTestCommand) -> tuple[TestDefinition, TestDraft]:
        slug = command.slug.strip().lower()
        name = command.name.strip()
        if not SLUG_RE.fullmatch(slug):
            raise ValueError("Invalid test slug")
        if not name:
            raise ValueError("Test name cannot be empty")
        if len(name) > 300:
            raise ValueError("Test name is too long")
        if HTML_TAG_RE.search(name):
            raise ValueError("HTML markup is not allowed in test name")
        if self._repository.get_test_by_slug(command.bot_instance_id, slug):
            raise TestSlugExists(slug)
        definition = TestDefinition(
            id=None,
            bot_instance_id=command.bot_instance_id,
            slug=slug,
            name=name,
            order=command.order,
        )
        draft = TestDraft(
            test_definition_id=0,
            name=name,
            schema=_EMPTY_SCHEMA,
        )
        return self._repository.create_test(definition, draft, created_by=command.created_by)


class GetTestDraft:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, test_id: int) -> TestDraft:
        draft = self._repository.get_draft(bot_instance_id, test_id)
        if draft is None:
            raise TestNotFound(test_id)
        return draft


class SaveTestDraft:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: SaveTestDraftCommand) -> TestDraft:
        if self._repository.get_test(command.bot_instance_id, command.test_id) is None:
            raise TestNotFound(command.test_id)
        name = command.name.strip()
        if not name or len(name) > 300:
            raise ValueError("Test name must contain between 1 and 300 characters")
        if HTML_TAG_RE.search(name):
            raise ValueError("HTML markup is not allowed in test name")
        if command.consent_document_id is not None:
            document = self._repository.get_consent_document(
                command.bot_instance_id, command.consent_document_id
            )
            if document is None:
                raise ConsentDocumentNotFound(command.consent_document_id)
        draft = TestDraft(
            test_definition_id=command.test_id,
            name=name,
            intro_text=command.intro_text,
            schema=validate_test_schema_draft(command.schema),
            revision=command.expected_revision,
            consent_enabled=command.consent_enabled,
            consent_document_id=command.consent_document_id,
            consent_checkbox_text=command.consent_checkbox_text,
            allow_retake=command.allow_retake,
            show_attempt_history=command.show_attempt_history,
            show_scores=command.show_scores,
        )
        return self._repository.save_draft(
            command.bot_instance_id,
            draft,
            expected_revision=command.expected_revision,
            updated_by=command.updated_by,
        )


class PublishTest:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: PublishTestCommand) -> PublishedTest:
        draft = self._repository.get_draft(command.bot_instance_id, command.test_id)
        if draft is None:
            raise TestNotFound(command.test_id)
        validate_test_schema(draft.schema)
        return self._repository.publish(
            command.bot_instance_id,
            command.test_id,
            expected_revision=command.expected_revision,
            published_by=command.published_by,
        )


class ReorderTests:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, test_ids: list[int]) -> list[TestDefinition]:
        if len(test_ids) != len(set(test_ids)):
            raise ValueError("Test order contains duplicate IDs")
        return self._repository.reorder(bot_instance_id, test_ids)


class PreviewTestResult:
    """Stateless: renders a submitted schema fragment against admin-supplied sample scale
    values, reusing the exact same `match_all_filters`/`render_result_template`/`split_message`
    functions `CompleteAttempt` calls at real completion time, so a previewed message cannot
    drift from what a student would actually receive (see Task 069)."""

    def execute(self, command: PreviewTestResultCommand) -> tuple[str, list[str]]:
        known_keys = set(command.sample_values)
        filters = validate_filters(command.filters, known_keys)
        template = validate_template(command.result_template, known_keys, require_non_blank=False)
        matched = match_all_filters(filters, command.sample_values)
        rendered = render_result_template(template, command.sample_values, matched)
        return rendered, split_message(rendered, MAX_MESSAGE_LENGTH)


# --- Consent documents (Task 073) ------------------------------------------------------------


class ListConsentDocuments:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int) -> list[ConsentDocument]:
        return self._repository.list_consent_documents(bot_instance_id)


class GetConsentDocument:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, document_id: int) -> ConsentDocument:
        document = self._repository.get_consent_document(bot_instance_id, document_id)
        if document is None:
            raise ConsentDocumentNotFound(document_id)
        return document


class CreateConsentDocument:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateConsentDocumentCommand) -> ConsentDocument:
        document = ConsentDocument(
            id=None,
            bot_instance_id=command.bot_instance_id,
            title=validate_consent_document_title(command.title),
            body_html=validate_consent_document_body(command.body_html),
            created_by=command.created_by,
            updated_by=command.created_by,
        )
        return self._repository.create_consent_document(document)


class UpdateConsentDocument:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateConsentDocumentCommand) -> ConsentDocument:
        updated = self._repository.update_consent_document(
            command.bot_instance_id,
            command.document_id,
            title=validate_consent_document_title(command.title),
            body_html=validate_consent_document_body(command.body_html),
            updated_by=command.updated_by,
        )
        if updated is None:
            raise ConsentDocumentNotFound(command.document_id)
        return updated


class DeleteConsentDocument:
    def __init__(self, repository: TestRepository) -> None:
        self._repository = repository

    def execute(self, bot_instance_id: int, document_id: int) -> None:
        if not self._repository.delete_consent_document(bot_instance_id, document_id):
            raise ConsentDocumentNotFound(document_id)
