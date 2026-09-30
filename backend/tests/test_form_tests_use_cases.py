from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.modules.form_tests.application.commands import (
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
from app.modules.form_tests.application.use_cases import (
    AttemptAlreadyCompleted,
    AttemptForbidden,
    AttemptNotFound,
    AutosaveAttempt,
    CompleteAttempt,
    ConsentCheckboxTextRequired,
    ConsentDocumentNotFound,
    ConsentRequired,
    CreateConsentDocument,
    CreateTest,
    DeleteConsentDocument,
    GetAttempt,
    GetAttemptDetailAdmin,
    GetConsentDocument,
    GetPublishedTest,
    GetTestDraft,
    ListActiveTests,
    ListAttemptsAdmin,
    ListConsentDocuments,
    ListMyAttempts,
    NothingToPublish,
    PreviewTestResult,
    PublishTest,
    ReorderTests,
    RetakeAttempt,
    RetakeNotAllowed,
    SaveTestDraft,
    StartOrResumeAttempt,
    TestDraftRevisionConflict,
    TestNotAvailable,
    TestNotFound,
    TestSlugExists,
    UpdateConsentDocument,
    UpdateTest,
)
from app.modules.form_tests.domain.consent import (
    CONSENT_DOCUMENT_LINK_PLACEHOLDER,
    consent_checkbox_text_is_valid,
)
from app.modules.form_tests.domain.entities import (
    ConsentDocument,
    PublishedTest,
    TestAttempt,
    TestAttemptStatus,
    TestDefinition,
    TestDraft,
    TestVersion,
)
from app.modules.form_tests.domain.errors import TestSchemaValidationError
from app.modules.form_tests.domain.schema import validate_test_schema
from app.modules.profiles.domain.entities import SharedProfile

_SCHEMA = validate_test_schema(
    {
        "elements": [
            {
                "key": "mood",
                "type": "single_choice",
                "label": "Настроение",
                "required": True,
                "scoring_key": "mood",
                "options": [
                    {"value": "good", "label": "Хорошо", "score": 0},
                    {"value": "bad", "label": "Плохо", "score": 10},
                ],
            }
        ],
        "result_scales": [
            {
                "key": "distress",
                "label": "Дистресс",
                "terms": [{"question_key": "mood", "weight": 1}],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        "filters": [],
        "result_template": "{{result:distress.value}}",
    }
)


class FakeTestRepository:
    def __init__(self) -> None:
        self._definitions: dict[int, TestDefinition] = {}
        self._versions: dict[int, TestVersion] = {}
        self._attempts: dict[int, TestAttempt] = {}
        self._drafts: dict[int, TestDraft] = {}
        self._consent_documents: dict[int, ConsentDocument] = {}
        self._next_id = 1

    def _allocate(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def seed_active_test(self, *, bot_instance_id: int) -> PublishedTest:
        definition_id = self._allocate()
        version_id = self._allocate()
        version = TestVersion(
            id=version_id,
            test_definition_id=definition_id,
            version=1,
            source_revision=0,
            name="Тест",
            intro_text=None,
            schema=_SCHEMA,
            published_by=None,
            published_at=datetime.now(tz=UTC),
        )
        definition = TestDefinition(
            id=definition_id,
            bot_instance_id=bot_instance_id,
            slug="test",
            is_active=True,
            is_archived=False,
            published_version_id=version_id,
        )
        self._definitions[definition_id] = definition
        self._versions[version_id] = version
        return PublishedTest(definition=definition, version=version)

    # --- TestRepository protocol -------------------------------------------------------

    def list_tests(self, bot_instance_id: int) -> list[TestDefinition]:
        return [d for d in self._definitions.values() if d.bot_instance_id == bot_instance_id]

    def list_active_published(self, bot_instance_id: int) -> list[PublishedTest]:
        return [
            PublishedTest(definition=d, version=self._versions[d.published_version_id])
            for d in self._definitions.values()
            if d.bot_instance_id == bot_instance_id and d.is_active and not d.is_archived
        ]

    def get_test(self, bot_instance_id: int, test_id: int) -> TestDefinition | None:
        d = self._definitions.get(test_id)
        return d if d and d.bot_instance_id == bot_instance_id else None

    def get_published(self, bot_instance_id: int, test_id: int) -> PublishedTest | None:
        d = self.get_test(bot_instance_id, test_id)
        if d is None or d.published_version_id is None:
            return None
        return PublishedTest(definition=d, version=self._versions[d.published_version_id])

    def get_version(self, bot_instance_id: int, test_id: int, version_id: int) -> PublishedTest | None:
        d = self.get_test(bot_instance_id, test_id)
        v = self._versions.get(version_id)
        if d is None or v is None or v.test_definition_id != test_id:
            return None
        return PublishedTest(definition=d, version=v)

    def get_test_by_slug(self, bot_instance_id: int, slug: str) -> TestDefinition | None:
        for d in self._definitions.values():
            if d.bot_instance_id == bot_instance_id and d.slug == slug:
                return d
        return None

    def get_draft(self, bot_instance_id: int, test_id: int) -> TestDraft | None:
        d = self.get_test(bot_instance_id, test_id)
        if d is None:
            return None
        return self._drafts.get(test_id)

    def update_test(self, definition: TestDefinition) -> TestDefinition:
        self._definitions[definition.id] = definition
        return definition

    def create_test(
        self, definition: TestDefinition, draft: TestDraft, *, created_by: int | None
    ) -> tuple[TestDefinition, TestDraft]:
        definition_id = self._allocate()
        stored_definition = replace(definition, id=definition_id, last_published_revision=-1)
        stored_draft = replace(draft, test_definition_id=definition_id, revision=0)
        self._definitions[definition_id] = stored_definition
        self._drafts[definition_id] = stored_draft
        return stored_definition, stored_draft

    def save_draft(
        self, bot_instance_id: int, draft: TestDraft, *, expected_revision: int, updated_by: int | None
    ) -> TestDraft:
        definition = self.get_test(bot_instance_id, draft.test_definition_id)
        if definition is None:
            raise LookupError(draft.test_definition_id)
        current = self._drafts[draft.test_definition_id]
        if current.revision != expected_revision:
            raise TestDraftRevisionConflict
        updated = replace(
            current,
            name=draft.name,
            intro_text=draft.intro_text,
            schema=draft.schema,
            consent_enabled=draft.consent_enabled,
            consent_document_id=draft.consent_document_id,
            consent_checkbox_text=draft.consent_checkbox_text,
            allow_retake=draft.allow_retake,
            show_attempt_history=draft.show_attempt_history,
            show_scores=draft.show_scores,
        )
        updated = replace(updated, revision=current.revision + 1)
        self._drafts[draft.test_definition_id] = updated
        self._definitions[draft.test_definition_id] = replace(definition, name=draft.name)
        return updated

    def publish(
        self, bot_instance_id: int, test_id: int, *, expected_revision: int, published_by: int | None
    ) -> PublishedTest:
        definition = self.get_test(bot_instance_id, test_id)
        draft = self._drafts.get(test_id)
        if definition is None or draft is None:
            raise LookupError(test_id)
        if draft.revision != expected_revision:
            raise TestDraftRevisionConflict
        if definition.last_published_revision >= draft.revision:
            raise NothingToPublish

        consent_document_title = None
        consent_document_body_html = None
        consent_checkbox_text = None
        if draft.consent_enabled:
            document = (
                self._consent_documents.get(draft.consent_document_id)
                if draft.consent_document_id is not None
                else None
            )
            if document is None or document.bot_instance_id != bot_instance_id:
                raise ConsentDocumentNotFound(draft.consent_document_id)
            if not draft.consent_checkbox_text or not consent_checkbox_text_is_valid(
                draft.consent_checkbox_text
            ):
                raise ConsentCheckboxTextRequired
            consent_document_title = document.title
            consent_document_body_html = document.body_html
            consent_checkbox_text = draft.consent_checkbox_text

        version_id = self._allocate()
        existing_versions = [v for v in self._versions.values() if v.test_definition_id == test_id]
        next_version = max((v.version for v in existing_versions), default=0) + 1
        version = TestVersion(
            id=version_id,
            test_definition_id=test_id,
            version=next_version,
            source_revision=draft.revision,
            name=draft.name,
            intro_text=draft.intro_text,
            schema=draft.schema,
            published_by=published_by,
            published_at=datetime.now(tz=UTC),
            consent_enabled=draft.consent_enabled,
            consent_document_title=consent_document_title,
            consent_document_body_html=consent_document_body_html,
            consent_checkbox_text=consent_checkbox_text,
            allow_retake=draft.allow_retake,
            show_attempt_history=draft.show_attempt_history,
            show_scores=draft.show_scores,
        )
        self._versions[version_id] = version
        updated_definition = replace(
            definition, published_version_id=version_id, last_published_revision=draft.revision
        )
        self._definitions[test_id] = updated_definition
        return PublishedTest(definition=updated_definition, version=version)

    def reorder(self, bot_instance_id: int, test_ids: list[int]) -> list[TestDefinition]:
        own = {d.id for d in self._definitions.values() if d.bot_instance_id == bot_instance_id}
        if own != set(test_ids):
            raise ValueError("Test order must include every test in the current bot")
        for order, test_id in enumerate(test_ids):
            self._definitions[test_id] = replace(self._definitions[test_id], order=order)
        return [self._definitions[test_id] for test_id in test_ids]

    def seed_published_test(self, **kwargs: Any) -> PublishedTest:  # pragma: no cover - unused here
        raise NotImplementedError

    def get_attempt(self, bot_instance_id: int, attempt_id: int) -> TestAttempt | None:
        a = self._attempts.get(attempt_id)
        return a if a and a.bot_instance_id == bot_instance_id else None

    def get_attempt_for_version(
        self, bot_instance_id: int, user_id: int, test_version_id: int
    ) -> TestAttempt | None:
        matches = [
            attempt
            for attempt in self._attempts.values()
            if attempt.bot_instance_id == bot_instance_id
            and attempt.user_id == user_id
            and attempt.test_version_id == test_version_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda a: (a.started_at, a.id))

    def delete_stale_in_progress_attempts(
        self, bot_instance_id: int, user_id: int, test_definition_id: int
    ) -> None:
        stale_ids = [
            attempt_id
            for attempt_id, attempt in self._attempts.items()
            if attempt.bot_instance_id == bot_instance_id
            and attempt.user_id == user_id
            and attempt.test_definition_id == test_definition_id
            and attempt.status == TestAttemptStatus.IN_PROGRESS
        ]
        for attempt_id in stale_ids:
            del self._attempts[attempt_id]

    def create_attempt(
        self, *, bot_instance_id: int, test_definition_id: int, test_version_id: int, user_id: int
    ) -> TestAttempt:
        attempt_id = self._allocate()
        attempt = TestAttempt(
            id=attempt_id,
            bot_instance_id=bot_instance_id,
            test_definition_id=test_definition_id,
            test_version_id=test_version_id,
            user_id=user_id,
            status=TestAttemptStatus.IN_PROGRESS,
            answers={},
            started_at=datetime.now(tz=UTC),
        )
        self._attempts[attempt_id] = attempt
        return attempt

    def save_attempt_answers(self, attempt_id: int, answers: dict) -> TestAttempt:
        attempt = self._attempts[attempt_id]
        updated = replace(attempt, answers={**attempt.answers, **answers})
        self._attempts[attempt_id] = updated
        return updated

    def complete_attempt(
        self,
        attempt_id: int,
        *,
        answers: dict,
        computed_results: dict,
        rendered_result_text: str,
        consent_accepted: bool = False,
        identity_snapshot: dict | None = None,
    ) -> TestAttempt:
        attempt = self._attempts[attempt_id]
        now = datetime.now(tz=UTC)
        updated = replace(
            attempt,
            answers=answers,
            computed_results=computed_results,
            rendered_result_text=rendered_result_text,
            status=TestAttemptStatus.COMPLETED,
            completed_at=now,
            consent_accepted=consent_accepted,
            consent_accepted_at=now if consent_accepted else None,
            identity_snapshot=identity_snapshot,
        )
        self._attempts[attempt_id] = updated
        return updated

    def list_attempts_for_user(self, bot_instance_id: int, user_id: int) -> list[TestAttempt]:
        result = []
        for attempt in self._attempts.values():
            if attempt.bot_instance_id != bot_instance_id or attempt.user_id != user_id:
                continue
            version = self._versions.get(attempt.test_version_id)
            if version is not None and not version.show_attempt_history:
                continue
            result.append(attempt)
        return result

    def list_attempts_for_test(
        self, bot_instance_id: int, test_definition_id: int, *, status: TestAttemptStatus | None = None
    ) -> list[TestAttempt]:
        return [
            a
            for a in self._attempts.values()
            if a.bot_instance_id == bot_instance_id
            and a.test_definition_id == test_definition_id
            and (status is None or a.status == status)
        ]

    # --- Consent documents (Task 073) ---------------------------------------------------

    def list_consent_documents(self, bot_instance_id: int) -> list[ConsentDocument]:
        return [d for d in self._consent_documents.values() if d.bot_instance_id == bot_instance_id]

    def get_consent_document(self, bot_instance_id: int, document_id: int) -> ConsentDocument | None:
        d = self._consent_documents.get(document_id)
        return d if d and d.bot_instance_id == bot_instance_id else None

    def create_consent_document(self, document: ConsentDocument) -> ConsentDocument:
        document_id = self._allocate()
        stored = replace(document, id=document_id)
        self._consent_documents[document_id] = stored
        return stored

    def update_consent_document(
        self, bot_instance_id: int, document_id: int, *, title: str, body_html: str, updated_by: int | None
    ) -> ConsentDocument | None:
        current = self.get_consent_document(bot_instance_id, document_id)
        if current is None:
            return None
        updated = replace(current, title=title, body_html=body_html, updated_by=updated_by)
        self._consent_documents[document_id] = updated
        return updated

    def delete_consent_document(self, bot_instance_id: int, document_id: int) -> bool:
        if self.get_consent_document(bot_instance_id, document_id) is None:
            return False
        del self._consent_documents[document_id]
        return True


class FakeDeliveryGateway:
    def __init__(self) -> None:
        self.deliveries: list[dict[str, Any]] = []

    def deliver_result(self, *, bot_instance_id: int, user_id: int, text: str) -> None:
        self.deliveries.append({"bot_instance_id": bot_instance_id, "user_id": user_id, "text": text})


class FakeProfileReader:
    """Task 080: a minimal `ProfileReader` stand-in -- one fixed profile (or none) regardless of
    `user_id`, which is all `CompleteAttempt`'s identity-snapshot coverage below needs."""

    def __init__(self, profile: SharedProfile | None) -> None:
        self._profile = profile

    def get_shared_profile(self, user_id: int) -> SharedProfile | None:
        return self._profile


BOT = 1
OTHER_BOT = 2
USER = 10
OTHER_USER = 20


def test_list_and_get_published_test_enforce_availability() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)

    assert ListActiveTests(repo).execute(BOT) == [published]
    assert GetPublishedTest(repo).execute(BOT, published.definition.id) == published

    with pytest.raises(TestNotFound):
        GetPublishedTest(repo).execute(BOT, 999)
    with pytest.raises(TestNotFound):
        GetPublishedTest(repo).execute(OTHER_BOT, published.definition.id)  # cross-tenant


def test_get_published_test_rejects_inactive_or_archived() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    repo.update_test(replace(published.definition, is_active=False))
    with pytest.raises(TestNotAvailable):
        GetPublishedTest(repo).execute(BOT, published.definition.id)


def test_start_attempt_resumes_existing_in_progress_attempt() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    first = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    second = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    assert first.id == second.id


def test_start_attempt_returns_completed_attempt_instead_of_duplicating() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    published = repo.seed_active_test(bot_instance_id=BOT)
    started = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id, answers={"mood": "bad"})
    )
    completed = CompleteAttempt(repo, delivery).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id)
    )

    reopened = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)

    assert reopened.id == completed.id
    assert reopened.status == TestAttemptStatus.COMPLETED


def test_complete_attempt_freezes_identity_snapshot_from_profile() -> None:
    """Task 080: the anketa no longer asks for name/birth date/email itself -- `CompleteAttempt`
    freezes them from the shared profile once, at completion, so a later profile edit can never
    retroactively change what an already-completed attempt reports."""
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    profile = SharedProfile(
        user_id=USER,
        external_user_id="ext-1",
        provider="max",
        last_name="Иванов",
        first_name="Иван",
        patronymic="Иванович",
        birth_date=date(2000, 1, 2),
        email="ivan@example.com",
    )
    published = repo.seed_active_test(bot_instance_id=BOT)
    started = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id, answers={"mood": "bad"})
    )
    completed = CompleteAttempt(repo, delivery, FakeProfileReader(profile)).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id)
    )

    assert completed.identity_snapshot == {
        "last_name": "Иванов",
        "first_name": "Иван",
        "patronymic": "Иванович",
        "birth_date": "2000-01-02",
        "email": "ivan@example.com",
    }


def test_complete_attempt_without_a_profile_reader_freezes_no_identity() -> None:
    """Every existing call site that constructs `CompleteAttempt(repo, delivery)` without a third
    argument (this file had a dozen before Task 080) must keep working unchanged."""
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    published = repo.seed_active_test(bot_instance_id=BOT)
    started = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id, answers={"mood": "bad"})
    )
    completed = CompleteAttempt(repo, delivery).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=started.id)
    )
    assert completed.identity_snapshot == dict.fromkeys(
        ("last_name", "first_name", "patronymic", "birth_date", "email")
    )


def test_autosave_rejects_other_users_attempt() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    with pytest.raises(AttemptForbidden):
        AutosaveAttempt(repo).execute(
            AutosaveAttemptCommand(
                bot_instance_id=BOT, user_id=OTHER_USER, attempt_id=attempt.id, answers={"mood": "good"}
            )
        )


def test_autosave_persists_partial_answers() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    saved = AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )
    assert saved.answers == {"mood": "bad"}


def test_complete_attempt_scores_persists_and_delivers() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )
    completed = CompleteAttempt(repo, delivery).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id)
    )
    assert completed.status == TestAttemptStatus.COMPLETED
    assert completed.computed_results["distress"]["value"] == 10
    assert completed.rendered_result_text == "10"
    assert delivery.deliveries == [{"bot_instance_id": BOT, "user_id": USER, "text": "10"}]

    with pytest.raises(AttemptAlreadyCompleted):
        CompleteAttempt(repo, delivery).execute(
            CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id)
        )


def test_complete_attempt_requires_the_required_question() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    with pytest.raises(Exception):  # TestAnswerValidationError bubbles up from the domain layer
        CompleteAttempt(repo, delivery).execute(
            CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id)
        )
    assert delivery.deliveries == []


def test_get_attempt_and_list_my_attempts_scope_to_owner() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)

    assert GetAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id) == attempt
    with pytest.raises(AttemptForbidden):
        GetAttempt(repo).execute(bot_instance_id=BOT, user_id=OTHER_USER, attempt_id=attempt.id)
    with pytest.raises(AttemptNotFound):
        GetAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, attempt_id=999)

    assert ListMyAttempts(repo).execute(BOT, USER) == [attempt]
    assert ListMyAttempts(repo).execute(BOT, OTHER_USER) == []


def test_admin_update_test_toggle_and_archive_deactivates() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    updated = UpdateTest(repo).execute(
        UpdateTestCommand(bot_instance_id=BOT, test_id=published.definition.id, is_archived=True)
    )
    assert updated.is_archived is True
    assert updated.is_active is False  # archiving forces deactivation


def test_admin_list_and_get_attempt_scope_to_the_named_test() -> None:
    repo = FakeTestRepository()
    published = repo.seed_active_test(bot_instance_id=BOT)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)

    assert ListAttemptsAdmin(repo).execute(BOT, published.definition.id) == [attempt]
    assert GetAttemptDetailAdmin(repo).execute(BOT, published.definition.id, attempt.id) == attempt
    with pytest.raises(AttemptNotFound):
        GetAttemptDetailAdmin(repo).execute(BOT, published.definition.id + 999, attempt.id)


# --- Admin constructor (Task 069) -----------------------------------------------------------

# Raw (not pre-normalized) schema, shaped exactly like what an admin's PUT/POST body would
# actually contain -- unlike `_SCHEMA` above, which is `validate_test_schema`'s own *normalized*
# output (every term carries both `question_key` and `result_scale_key`, one of them `None`) and
# is therefore not valid raw input to feed back into the same validator a second time.
_RAW_SCHEMA: dict[str, Any] = {
    "elements": [
        {
            "key": "mood",
            "type": "single_choice",
            "label": "Настроение",
            "required": True,
            "scoring_key": "mood",
            "options": [
                {"value": "good", "label": "Хорошо", "score": 0},
                {"value": "bad", "label": "Плохо", "score": 10},
            ],
        }
    ],
    "result_scales": [
        {
            "key": "distress",
            "label": "Дистресс",
            "terms": [{"question_key": "mood", "weight": 1}],
            "constant": 0,
            "aggregation": "sum",
        }
    ],
    "filters": [],
    "result_template": "{{result:distress.value}}",
}


def test_create_test_rejects_duplicate_slug_case_insensitive() -> None:
    repo = FakeTestRepository()
    CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="spt", name="СПТ", order=0, created_by=None)
    )
    with pytest.raises(TestSlugExists):
        CreateTest(repo).execute(
            CreateTestCommand(bot_instance_id=BOT, slug="SPT", name="Другое имя", order=1, created_by=None)
        )
    # same slug in a different bot is fine -- uniqueness is per-tenant
    CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=OTHER_BOT, slug="spt", name="СПТ", order=0, created_by=None)
    )


def test_create_test_starts_with_an_empty_but_saveable_draft() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=7)
    )
    assert draft.revision == 0
    assert draft.schema == {"elements": [], "result_scales": [], "filters": [], "result_template": ""}
    assert definition.last_published_revision == -1


def test_save_test_draft_accepts_incomplete_schema_but_rejects_malformed_elements() -> None:
    repo = FakeTestRepository()
    definition, _ = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    # No result scale yet -- would fail the strict validator, must succeed for a draft save.
    saved = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=0,
            name="Квиз",
            intro_text=None,
            schema={
                "elements": [{"key": "q1", "type": "instruction", "label": "Инструкция"}],
                "result_scales": [],
                "filters": [],
                "result_template": "",
            },
            updated_by=None,
        )
    )
    assert saved.revision == 1
    assert len(saved.schema["elements"]) == 1

    with pytest.raises(TestSchemaValidationError):
        SaveTestDraft(repo).execute(
            SaveTestDraftCommand(
                bot_instance_id=BOT,
                test_id=definition.id,
                expected_revision=1,
                name="Квиз",
                intro_text=None,
                schema={
                    "elements": [{"key": "q1", "type": "not_a_real_type", "label": "x"}],
                    "result_scales": [],
                    "filters": [],
                    "result_template": "",
                },
                updated_by=None,
            )
        )


def test_save_test_draft_revision_conflict() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    with pytest.raises(TestDraftRevisionConflict):
        SaveTestDraft(repo).execute(
            SaveTestDraftCommand(
                bot_instance_id=BOT,
                test_id=definition.id,
                expected_revision=draft.revision + 1,  # stale
                name="Квиз",
                intro_text=None,
                schema=draft.schema,
                updated_by=None,
            )
        )


def test_publish_test_requires_the_full_strict_schema() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    # The blank starter draft has no result scale -- publish must reject it, unlike a draft save.
    with pytest.raises(TestSchemaValidationError):
        PublishTest(repo).execute(
            PublishTestCommand(
                bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
            )
        )


def test_publish_test_succeeds_after_a_draft_save_normalizes_a_text_element() -> None:
    """Regression: `SaveTestDraft` stores `validate_test_schema_draft`'s *normalized* output, and
    `PublishTest` re-validates that same stored (already-normalized) schema with the strict
    validator -- so any element type whose normalized shape isn't valid raw input to
    `validate_elements` a second time would always fail publish after a save, for every test
    containing one, not just in an isolated unit test. A `text` element specifically used to gain
    a stray `scoring_key: None` in its normalized output that `validate_elements`' own
    "unknown properties" check then rejected on the next pass (`text` isn't in `CHOICE_TYPES`, so
    `scoring_key` was never in its `allowed` set) -- caught via a real end-to-end HTTP smoke test
    against RUT's own 252-element content (which is full of exactly this), not by any of this
    file's other tests, none of which previously mixed a `text` element with a save-then-publish
    round trip."""
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    schema = {
        "elements": [
            {"key": "name", "type": "text", "label": "Ваше имя"},
            {
                "key": "mood",
                "type": "single_choice",
                "label": "Настроение",
                "scoring_key": "mood",
                "options": [{"value": "good", "label": "Хорошо", "score": 1}],
            },
        ],
        "result_scales": [
            {
                "key": "distress",
                "label": "Дистресс",
                "terms": [{"question_key": "mood", "weight": 1}],
                "constant": 0,
                "aggregation": "sum",
            }
        ],
        "filters": [],
        "result_template": "{{result:distress.value}}",
    }
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=schema,
            updated_by=None,
        )
    )
    published = PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    assert published.version.version == 1


def test_publish_test_creates_a_version_without_mutating_a_prior_one() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
        )
    )
    published_v1 = PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    assert published_v1.version.version == 1
    UpdateTest(repo).execute(UpdateTestCommand(bot_instance_id=BOT, test_id=definition.id, is_active=True))

    # A completed attempt against v1 must survive publishing v2 untouched.
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    assert attempt.test_version_id == published_v1.version.id

    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз v2",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
        )
    )
    published_v2 = PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    assert published_v2.version.version == 2
    assert published_v2.version.id != published_v1.version.id

    # v1 itself is untouched, and the already-started attempt still points at it.
    v1_again = repo.get_version(BOT, definition.id, published_v1.version.id)
    assert v1_again is not None
    assert v1_again.version.name == "Квиз"
    still_there = repo.get_attempt(BOT, attempt.id)
    assert still_there is not None
    assert still_there.test_version_id == published_v1.version.id


def test_publish_test_nothing_to_publish_without_a_new_draft_revision() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
        )
    )
    PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    with pytest.raises(NothingToPublish):
        PublishTest(repo).execute(
            PublishTestCommand(
                bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
            )
        )


def test_get_test_draft_is_cross_tenant_scoped() -> None:
    repo = FakeTestRepository()
    definition, _ = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    assert GetTestDraft(repo).execute(BOT, definition.id).name == "Квиз"
    with pytest.raises(TestNotFound):
        GetTestDraft(repo).execute(OTHER_BOT, definition.id)


def test_reorder_tests_rejects_a_partial_or_duplicate_id_list() -> None:
    repo = FakeTestRepository()
    a, _ = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="aa", name="A", order=0, created_by=None)
    )
    b, _ = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="bb", name="B", order=1, created_by=None)
    )
    with pytest.raises(ValueError):
        ReorderTests(repo).execute(BOT, [a.id, a.id])
    with pytest.raises(ValueError):
        ReorderTests(repo).execute(BOT, [a.id])  # missing b
    reordered = ReorderTests(repo).execute(BOT, [b.id, a.id])
    assert [d.id for d in reordered] == [b.id, a.id]


def test_preview_test_result_matches_the_real_render_and_split_path() -> None:
    from app.modules.form_tests.domain.filters import match_all_filters
    from app.modules.form_tests.domain.message_split import split_message
    from app.modules.form_tests.domain.template import render_result_template

    command = PreviewTestResultCommand(
        filters=[
            {
                "result_scale_key": "distress",
                "rules": [{"min": 5, "max": None, "label": "Высокий", "is_flagged": True, "recommendation_text": "см. специалиста"}],
            }
        ],
        result_template="{{result:distress.value}} — {{result:distress.label}}",
        sample_values={"distress": 10},
    )
    rendered_text, chunks = PreviewTestResult().execute(command)

    matched = match_all_filters(command.filters, command.sample_values)
    expected_text = render_result_template(command.result_template, command.sample_values, matched)
    assert rendered_text == expected_text
    assert chunks == split_message(expected_text, 4000)


# --- Participation consent (Task 073) --------------------------------------------------------

_CHECKBOX_TEXT = f"Я согласен на участие в исследовании. {CONSENT_DOCUMENT_LINK_PLACEHOLDER}"


def _create_document(repo: FakeTestRepository, *, bot_instance_id: int = BOT) -> ConsentDocument:
    return CreateConsentDocument(repo).execute(
        CreateConsentDocumentCommand(
            bot_instance_id=bot_instance_id,
            title="Согласие на участие в исследовании",
            body_html="<p>Текст документа.</p>",
            created_by=None,
        )
    )


def test_consent_document_crud_is_tenant_scoped() -> None:
    repo = FakeTestRepository()
    document = _create_document(repo)
    assert ListConsentDocuments(repo).execute(BOT) == [document]
    assert ListConsentDocuments(repo).execute(OTHER_BOT) == []
    assert GetConsentDocument(repo).execute(BOT, document.id) == document
    with pytest.raises(ConsentDocumentNotFound):
        GetConsentDocument(repo).execute(OTHER_BOT, document.id)

    updated = UpdateConsentDocument(repo).execute(
        UpdateConsentDocumentCommand(
            bot_instance_id=BOT,
            document_id=document.id,
            title="Новое название",
            body_html="<p>Новый текст.</p>",
            updated_by=None,
        )
    )
    assert updated.title == "Новое название"
    with pytest.raises(ConsentDocumentNotFound):
        UpdateConsentDocument(repo).execute(
            UpdateConsentDocumentCommand(
                bot_instance_id=OTHER_BOT,
                document_id=document.id,
                title="x",
                body_html="<p>x</p>",
                updated_by=None,
            )
        )

    with pytest.raises(ConsentDocumentNotFound):
        DeleteConsentDocument(repo).execute(OTHER_BOT, document.id)
    DeleteConsentDocument(repo).execute(BOT, document.id)
    assert ListConsentDocuments(repo).execute(BOT) == []


def test_save_test_draft_rejects_an_unresolvable_consent_document() -> None:
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    with pytest.raises(ConsentDocumentNotFound):
        SaveTestDraft(repo).execute(
            SaveTestDraftCommand(
                bot_instance_id=BOT,
                test_id=definition.id,
                expected_revision=draft.revision,
                name="Квиз",
                intro_text=None,
                schema=draft.schema,
                updated_by=None,
                consent_enabled=True,
                consent_document_id=999,
                consent_checkbox_text=_CHECKBOX_TEXT,
            )
        )

    # A cross-tenant document id is just as unresolvable.
    other_bot_document = _create_document(repo, bot_instance_id=OTHER_BOT)
    with pytest.raises(ConsentDocumentNotFound):
        SaveTestDraft(repo).execute(
            SaveTestDraftCommand(
                bot_instance_id=BOT,
                test_id=definition.id,
                expected_revision=draft.revision,
                name="Квиз",
                intro_text=None,
                schema=draft.schema,
                updated_by=None,
                consent_enabled=True,
                consent_document_id=other_bot_document.id,
                consent_checkbox_text=_CHECKBOX_TEXT,
            )
        )


def test_save_test_draft_allows_consent_enabled_with_no_document_picked_yet() -> None:
    """Draft save is permissive (Task 069's split): an admin mid-authoring may turn the toggle on
    before picking a document -- only publish requires the full, resolvable configuration."""
    repo = FakeTestRepository()
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    saved = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=draft.schema,
            updated_by=None,
            consent_enabled=True,
            consent_document_id=None,
            consent_checkbox_text=None,
        )
    )
    assert saved.consent_enabled is True
    assert saved.consent_document_id is None


def test_publish_test_requires_a_resolvable_document_and_valid_checkbox_text() -> None:
    repo = FakeTestRepository()
    document = _create_document(repo)
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
            consent_enabled=True,
            consent_document_id=None,
            consent_checkbox_text=None,
        )
    )
    with pytest.raises(ConsentDocumentNotFound):
        PublishTest(repo).execute(
            PublishTestCommand(
                bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
            )
        )

    # A picked document but a checkbox text missing the click-inserted link placeholder.
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
            consent_enabled=True,
            consent_document_id=document.id,
            consent_checkbox_text="Я согласен, но без ссылки на документ",
        )
    )
    with pytest.raises(ConsentCheckboxTextRequired):
        PublishTest(repo).execute(
            PublishTestCommand(
                bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
            )
        )


def test_publish_test_freezes_the_consent_document_content() -> None:
    repo = FakeTestRepository()
    document = _create_document(repo)
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
            consent_enabled=True,
            consent_document_id=document.id,
            consent_checkbox_text=_CHECKBOX_TEXT,
        )
    )
    published = PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    assert published.version.consent_enabled is True
    assert published.version.consent_document_title == document.title
    assert published.version.consent_document_body_html == document.body_html
    assert published.version.consent_checkbox_text == _CHECKBOX_TEXT

    # Editing the source document afterward must never change the already-published version.
    UpdateConsentDocument(repo).execute(
        UpdateConsentDocumentCommand(
            bot_instance_id=BOT,
            document_id=document.id,
            title="Изменённое название",
            body_html="<p>Изменённый текст.</p>",
            updated_by=None,
        )
    )
    still_frozen = repo.get_version(BOT, definition.id, published.version.id)
    assert still_frozen is not None
    assert still_frozen.version.consent_document_title == document.title
    assert still_frozen.version.consent_document_body_html == document.body_html


def test_complete_attempt_requires_consent_when_the_version_enables_it() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    document = _create_document(repo)
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug="quiz", name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
            consent_enabled=True,
            consent_document_id=document.id,
            consent_checkbox_text=_CHECKBOX_TEXT,
        )
    )
    published = PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    UpdateTest(repo).execute(UpdateTestCommand(bot_instance_id=BOT, test_id=definition.id, is_active=True))
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )

    with pytest.raises(ConsentRequired):
        CompleteAttempt(repo, delivery).execute(
            CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, consent_accepted=False)
        )
    assert delivery.deliveries == []
    # A rejected completion leaves the attempt untouched -- still in_progress, retriable.
    still_in_progress = repo.get_attempt(BOT, attempt.id)
    assert still_in_progress is not None
    assert still_in_progress.status == TestAttemptStatus.IN_PROGRESS

    completed = CompleteAttempt(repo, delivery).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, consent_accepted=True)
    )
    assert completed.status == TestAttemptStatus.COMPLETED
    assert completed.consent_accepted is True
    assert completed.consent_accepted_at is not None
    assert published.version.id == completed.test_version_id


def test_complete_attempt_ignores_consent_flag_when_not_required() -> None:
    """A test with no consent configured must keep working exactly as before -- Task 073 is
    strictly additive and opt-in per test."""
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    published = repo.seed_active_test(bot_instance_id=BOT)
    assert published.version.consent_enabled is False
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=published.definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )
    completed = CompleteAttempt(repo, delivery).execute(
        CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, consent_accepted=False)
    )
    assert completed.status == TestAttemptStatus.COMPLETED
    assert completed.consent_accepted is False
    assert completed.consent_accepted_at is None


# --- Retake, attempt-history visibility, and score visibility (Task 075) --------------------


def _create_and_publish_test(
    repo: FakeTestRepository,
    *,
    slug: str = "quiz",
    allow_retake: bool = False,
    show_attempt_history: bool = True,
    show_scores: bool = False,
) -> TestDefinition:
    definition, draft = CreateTest(repo).execute(
        CreateTestCommand(bot_instance_id=BOT, slug=slug, name="Квиз", order=0, created_by=None)
    )
    draft = SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
            allow_retake=allow_retake,
            show_attempt_history=show_attempt_history,
            show_scores=show_scores,
        )
    )
    PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )
    UpdateTest(repo).execute(UpdateTestCommand(bot_instance_id=BOT, test_id=definition.id, is_active=True))
    return definition


def test_publish_freezes_attempt_settings_onto_the_version() -> None:
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo, allow_retake=True, show_attempt_history=False, show_scores=True)
    published = GetPublishedTest(repo).execute(BOT, definition.id)
    assert published.version.allow_retake is True
    assert published.version.show_attempt_history is False
    assert published.version.show_scores is True


def test_new_test_defaults_preserve_pre_075_behavior() -> None:
    """A test created without ever touching these settings behaves exactly as this module did
    before Task 075: single attempt, full history, no scores shown."""
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo)
    published = GetPublishedTest(repo).execute(BOT, definition.id)
    assert published.version.allow_retake is False
    assert published.version.show_attempt_history is True
    assert published.version.show_scores is False


def test_reopening_a_completed_test_always_returns_the_existing_result() -> None:
    """Confirmed product decision: a plain re-open (not an explicit retake) always shows the
    existing completed attempt, never a fresh one and never an error -- regardless of
    `allow_retake`, which only affects the separate, explicit `RetakeAttempt` action."""
    for allow_retake in (False, True):
        repo = FakeTestRepository()
        delivery = FakeDeliveryGateway()
        definition = _create_and_publish_test(repo, allow_retake=allow_retake)
        attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
        AutosaveAttempt(repo).execute(
            AutosaveAttemptCommand(
                bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"}
            )
        )
        completed = CompleteAttempt(repo, delivery).execute(
            CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id)
        )
        reopened = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
        assert reopened.id == completed.id
        assert reopened.status == TestAttemptStatus.COMPLETED


def test_republishing_mid_attempt_does_not_leave_a_duplicate_in_progress_row() -> None:
    """Regression test: a student starts a test, then the admin edits and republishes it (a new
    `TestVersion`) while that attempt is still in progress, then the student reopens the test
    again. `StartOrResumeAttempt` only ever resolves an existing attempt against the *current*
    published version, so before this fix the first, now-superseded attempt was silently
    orphaned -- left `in_progress` forever and piling up as a duplicate tile in the student's own
    history (`ListMyAttempts`) every time this repeated. It must be replaced, not accumulated."""
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo)
    first = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    assert first.status == TestAttemptStatus.IN_PROGRESS

    # Admin edits and republishes the test in the constructor while the attempt above is still
    # in progress -- a new `TestVersion` is created, `first` now points at a superseded one.
    draft = GetTestDraft(repo).execute(BOT, definition.id)
    SaveTestDraft(repo).execute(
        SaveTestDraftCommand(
            bot_instance_id=BOT,
            test_id=definition.id,
            expected_revision=draft.revision,
            name="Квиз (обновлён)",
            intro_text=None,
            schema=_RAW_SCHEMA,
            updated_by=None,
        )
    )
    draft = GetTestDraft(repo).execute(BOT, definition.id)
    PublishTest(repo).execute(
        PublishTestCommand(
            bot_instance_id=BOT, test_id=definition.id, expected_revision=draft.revision, published_by=None
        )
    )

    second = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    assert second.id != first.id
    assert second.status == TestAttemptStatus.IN_PROGRESS

    # The orphaned attempt against the old version must be gone, not just ignored -- otherwise it
    # keeps showing up as an extra "in progress" tile forever.
    assert repo.get_attempt(BOT, first.id) is None
    attempts = ListMyAttempts(repo).execute(BOT, USER)
    assert [a.id for a in attempts] == [second.id]


def test_retake_creates_an_independent_new_attempt_when_allowed() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    definition = _create_and_publish_test(repo, allow_retake=True)
    first = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=first.id, answers={"mood": "bad"})
    )
    CompleteAttempt(repo, delivery).execute(CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=first.id))

    retaken = RetakeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    assert retaken.id != first.id
    assert retaken.status == TestAttemptStatus.IN_PROGRESS

    # The previous attempt survives untouched.
    still_there = repo.get_attempt(BOT, first.id)
    assert still_there is not None
    assert still_there.status == TestAttemptStatus.COMPLETED

    # Both now show up for the student -- history stays on by default.
    attempts = ListMyAttempts(repo).execute(BOT, USER)
    assert {a.id for a in attempts} == {first.id, retaken.id}


def test_retake_rejected_when_the_version_disallows_it() -> None:
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    definition = _create_and_publish_test(repo, allow_retake=False)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )
    CompleteAttempt(repo, delivery).execute(CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id))
    with pytest.raises(RetakeNotAllowed):
        RetakeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)


def test_retake_rejected_without_a_completed_attempt_yet() -> None:
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo, allow_retake=True)
    with pytest.raises(RetakeNotAllowed):
        RetakeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)


def test_retake_is_cross_tenant_scoped() -> None:
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo, allow_retake=True)
    with pytest.raises(TestNotFound):
        RetakeAttempt(repo).execute(bot_instance_id=OTHER_BOT, user_id=USER, test_id=definition.id)


def test_retake_is_scoped_to_the_calling_user() -> None:
    """User B has no completed attempt of their own to retake from, even though user A does --
    retake never reads or is satisfied by another user's attempt state."""
    repo = FakeTestRepository()
    delivery = FakeDeliveryGateway()
    definition = _create_and_publish_test(repo, allow_retake=True)
    attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    AutosaveAttempt(repo).execute(
        AutosaveAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"})
    )
    CompleteAttempt(repo, delivery).execute(CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id))

    with pytest.raises(RetakeNotAllowed):
        RetakeAttempt(repo).execute(bot_instance_id=BOT, user_id=OTHER_USER, test_id=definition.id)


def test_retake_resumes_an_in_progress_attempt_instead_of_erroring() -> None:
    repo = FakeTestRepository()
    definition = _create_and_publish_test(repo, allow_retake=True)
    started = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    resumed = RetakeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
    assert resumed.id == started.id
    assert resumed.status == TestAttemptStatus.IN_PROGRESS


def test_use_case_layer_always_returns_true_computed_results_regardless_of_show_scores() -> None:
    """`show_scores` redaction happens only at the presentation layer (`_attempt_out` in
    `presentation/router.py`, covered by `test_form_tests_router.py`) -- the domain/use-case layer
    (and every repository read behind it, including the admin-facing ones) always stays truthful,
    the same way `_student_safe_elements` redacts option scores only at the API boundary rather
    than mutating stored/domain data (Task 075)."""
    delivery = FakeDeliveryGateway()
    for show_scores in (False, True):
        repo = FakeTestRepository()
        definition = _create_and_publish_test(repo, slug="quiz", show_scores=show_scores)
        attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
        AutosaveAttempt(repo).execute(
            AutosaveAttemptCommand(
                bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id, answers={"mood": "bad"}
            )
        )
        completed = CompleteAttempt(repo, delivery).execute(
            CompleteAttemptCommand(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id)
        )
        expected = {"distress": {"value": 10, "aggregation": "sum", "filter": None}}
        assert completed.computed_results == expected
        assert GetAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, attempt_id=attempt.id).computed_results == expected
        reopened = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=definition.id)
        assert reopened.computed_results == expected
        assert ListMyAttempts(repo).execute(BOT, USER)[0].computed_results == expected


def test_show_attempt_history_filters_the_students_list() -> None:
    repo = FakeTestRepository()
    visible = _create_and_publish_test(repo, slug="visible", show_attempt_history=True)
    hidden = _create_and_publish_test(repo, slug="hidden", show_attempt_history=False)

    visible_attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=visible.id)
    hidden_attempt = StartOrResumeAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, test_id=hidden.id)

    attempts = ListMyAttempts(repo).execute(BOT, USER)
    assert {a.id for a in attempts} == {visible_attempt.id}

    # A direct read of the hidden attempt (not a history listing) is unaffected by the flag.
    direct = GetAttempt(repo).execute(bot_instance_id=BOT, user_id=USER, attempt_id=hidden_attempt.id)
    assert direct.id == hidden_attempt.id
