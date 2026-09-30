from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..application.use_cases import (
    ConsentCheckboxTextRequired,
    ConsentDocumentNotFound,
    NothingToPublish,
    TestDraftRevisionConflict,
)
from ..domain.consent import consent_checkbox_text_is_valid
from ..domain.entities import (
    ConsentDocument,
    PublishedTest,
    TestAttempt,
    TestAttemptStatus,
    TestDefinition,
    TestDraft,
    TestVersion,
)
from .models import (
    ConsentDocumentRecord,
    TestAttemptRecord,
    TestDefinitionRecord,
    TestDraftRecord,
    TestVersionRecord,
)


def _definition(record: TestDefinitionRecord) -> TestDefinition:
    return TestDefinition(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        slug=record.slug,
        name=record.name,
        order=record.order,
        is_active=record.is_active,
        is_archived=record.is_archived,
        published_version_id=record.published_version_id,
        last_published_revision=record.last_published_revision,
    )


def _version(record: TestVersionRecord) -> TestVersion:
    return TestVersion(
        id=record.id,
        test_definition_id=record.test_definition_id,
        version=record.version,
        source_revision=record.source_revision,
        name=record.name,
        intro_text=record.intro_text,
        schema=record.schema,
        published_by=record.published_by,
        published_at=record.published_at,
        consent_enabled=record.consent_enabled,
        consent_document_title=record.consent_document_title,
        consent_document_body_html=record.consent_document_body_html,
        consent_checkbox_text=record.consent_checkbox_text,
        allow_retake=record.allow_retake,
        show_attempt_history=record.show_attempt_history,
        show_scores=record.show_scores,
    )


def _draft(record: TestDraftRecord) -> TestDraft:
    return TestDraft(
        test_definition_id=record.test_definition_id,
        name=record.name,
        intro_text=record.intro_text,
        schema=dict(record.schema or {}),
        revision=record.revision,
        updated_at=record.updated_at,
        consent_enabled=record.consent_enabled,
        consent_document_id=record.consent_document_id,
        consent_checkbox_text=record.consent_checkbox_text,
        allow_retake=record.allow_retake,
        show_attempt_history=record.show_attempt_history,
        show_scores=record.show_scores,
    )


def _attempt(record: TestAttemptRecord) -> TestAttempt:
    return TestAttempt(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        test_definition_id=record.test_definition_id,
        test_version_id=record.test_version_id,
        user_id=record.user_id,
        status=record.status,
        answers=dict(record.answers or {}),
        computed_results=dict(record.computed_results) if record.computed_results else None,
        rendered_result_text=record.rendered_result_text,
        started_at=record.started_at,
        completed_at=record.completed_at,
        consent_accepted=record.consent_accepted,
        consent_accepted_at=record.consent_accepted_at,
        identity_snapshot=dict(record.identity_snapshot) if record.identity_snapshot else None,
    )


def _consent_document(record: ConsentDocumentRecord) -> ConsentDocument:
    return ConsentDocument(
        id=record.id,
        bot_instance_id=record.bot_instance_id,
        title=record.title,
        body_html=record.body_html,
        created_by=record.created_by,
        updated_by=record.updated_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyTestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_tests(self, bot_instance_id: int) -> list[TestDefinition]:
        records = self._session.execute(
            select(TestDefinitionRecord)
            .where(TestDefinitionRecord.bot_instance_id == bot_instance_id)
            .order_by(TestDefinitionRecord.order, TestDefinitionRecord.id)
        ).scalars()
        return [_definition(record) for record in records]

    def list_active_published(self, bot_instance_id: int) -> list[PublishedTest]:
        rows = self._session.execute(
            select(TestDefinitionRecord, TestVersionRecord)
            .join(TestVersionRecord, TestVersionRecord.id == TestDefinitionRecord.published_version_id)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.is_active.is_(True),
                TestDefinitionRecord.is_archived.is_(False),
            )
            .order_by(TestDefinitionRecord.order, TestDefinitionRecord.id)
        ).all()
        return [
            PublishedTest(definition=_definition(definition), version=_version(version))
            for definition, version in rows
        ]

    def get_test(self, bot_instance_id: int, test_id: int) -> TestDefinition | None:
        record = self._session.execute(
            select(TestDefinitionRecord).where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.id == test_id,
            )
        ).scalar_one_or_none()
        return _definition(record) if record else None

    def get_published(self, bot_instance_id: int, test_id: int) -> PublishedTest | None:
        row = self._session.execute(
            select(TestDefinitionRecord, TestVersionRecord)
            .join(TestVersionRecord, TestVersionRecord.id == TestDefinitionRecord.published_version_id)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.id == test_id,
            )
        ).one_or_none()
        if row is None:
            return None
        definition, version = row
        return PublishedTest(definition=_definition(definition), version=_version(version))

    def get_version(self, bot_instance_id: int, test_id: int, version_id: int) -> PublishedTest | None:
        row = self._session.execute(
            select(TestDefinitionRecord, TestVersionRecord)
            .join(TestVersionRecord, TestVersionRecord.test_definition_id == TestDefinitionRecord.id)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.id == test_id,
                TestVersionRecord.id == version_id,
            )
        ).one_or_none()
        if row is None:
            return None
        definition, version = row
        return PublishedTest(definition=_definition(definition), version=_version(version))

    def get_test_by_slug(self, bot_instance_id: int, slug: str) -> TestDefinition | None:
        record = self._session.execute(
            select(TestDefinitionRecord).where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.slug == slug,
            )
        ).scalar_one_or_none()
        return _definition(record) if record else None

    def get_draft(self, bot_instance_id: int, test_id: int) -> TestDraft | None:
        record = self._session.execute(
            select(TestDraftRecord)
            .join(TestDefinitionRecord, TestDefinitionRecord.id == TestDraftRecord.test_definition_id)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDraftRecord.test_definition_id == test_id,
            )
        ).scalar_one_or_none()
        return _draft(record) if record else None

    def update_test(self, definition: TestDefinition) -> TestDefinition:
        record = self._session.execute(
            select(TestDefinitionRecord).where(
                TestDefinitionRecord.id == definition.id,
                TestDefinitionRecord.bot_instance_id == definition.bot_instance_id,
            )
        ).scalar_one()
        record.is_active = definition.is_active
        record.is_archived = definition.is_archived
        self._session.flush()
        return _definition(record)

    def create_test(
        self,
        definition: TestDefinition,
        draft: TestDraft,
        *,
        created_by: int | None,
    ) -> tuple[TestDefinition, TestDraft]:
        record = TestDefinitionRecord(
            bot_instance_id=definition.bot_instance_id,
            slug=definition.slug,
            order=definition.order,
            is_active=False,
            is_archived=False,
            last_published_revision=-1,
            name=draft.name,
            created_by=created_by,
        )
        self._session.add(record)
        self._session.flush()
        draft_record = TestDraftRecord(
            test_definition_id=record.id,
            name=draft.name,
            intro_text=draft.intro_text,
            schema=draft.schema,
            revision=0,
            updated_by=created_by,
        )
        self._session.add(draft_record)
        self._session.flush()
        return _definition(record), _draft(draft_record)

    def save_draft(
        self,
        bot_instance_id: int,
        draft: TestDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> TestDraft:
        record = self._session.execute(
            select(TestDraftRecord)
            .join(TestDefinitionRecord, TestDefinitionRecord.id == TestDraftRecord.test_definition_id)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDraftRecord.test_definition_id == draft.test_definition_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if record is None:
            raise LookupError(draft.test_definition_id)
        if record.revision != expected_revision:
            raise TestDraftRevisionConflict
        record.name = draft.name
        record.intro_text = draft.intro_text
        record.schema = draft.schema
        record.revision += 1
        record.updated_by = updated_by
        record.consent_enabled = draft.consent_enabled
        record.consent_document_id = draft.consent_document_id
        record.consent_checkbox_text = draft.consent_checkbox_text
        record.allow_retake = draft.allow_retake
        record.show_attempt_history = draft.show_attempt_history
        record.show_scores = draft.show_scores

        definition = self._session.get(TestDefinitionRecord, draft.test_definition_id)
        assert definition is not None
        definition.name = draft.name
        self._session.flush()
        return _draft(record)

    def publish(
        self,
        bot_instance_id: int,
        test_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedTest:
        definition = self._session.execute(
            select(TestDefinitionRecord)
            .where(
                TestDefinitionRecord.bot_instance_id == bot_instance_id,
                TestDefinitionRecord.id == test_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        draft = self._session.execute(
            select(TestDraftRecord).where(TestDraftRecord.test_definition_id == test_id).with_for_update()
        ).scalar_one_or_none()
        if definition is None or draft is None:
            raise LookupError(test_id)
        if draft.revision != expected_revision:
            raise TestDraftRevisionConflict
        if definition.last_published_revision >= draft.revision:
            raise NothingToPublish

        consent_document_title: str | None = None
        consent_document_body_html: str | None = None
        consent_checkbox_text: str | None = None
        if draft.consent_enabled:
            document = (
                self._session.execute(
                    select(ConsentDocumentRecord).where(
                        ConsentDocumentRecord.bot_instance_id == bot_instance_id,
                        ConsentDocumentRecord.id == draft.consent_document_id,
                    )
                ).scalar_one_or_none()
                if draft.consent_document_id is not None
                else None
            )
            if document is None:
                raise ConsentDocumentNotFound(draft.consent_document_id)
            if not draft.consent_checkbox_text or not consent_checkbox_text_is_valid(
                draft.consent_checkbox_text
            ):
                raise ConsentCheckboxTextRequired
            consent_document_title = document.title
            consent_document_body_html = document.body_html
            consent_checkbox_text = draft.consent_checkbox_text

        next_version = (
            self._session.execute(
                select(func.max(TestVersionRecord.version)).where(
                    TestVersionRecord.test_definition_id == test_id
                )
            ).scalar_one()
            or 0
        ) + 1
        version = TestVersionRecord(
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
        self._session.add(version)
        self._session.flush()
        definition.published_version_id = version.id
        definition.last_published_revision = draft.revision
        self._session.flush()
        return PublishedTest(definition=_definition(definition), version=_version(version))

    def reorder(self, bot_instance_id: int, test_ids: list[int]) -> list[TestDefinition]:
        records = list(
            self._session.execute(
                select(TestDefinitionRecord)
                .where(TestDefinitionRecord.bot_instance_id == bot_instance_id)
                .with_for_update()
            ).scalars()
        )
        if {record.id for record in records} != set(test_ids):
            raise ValueError("Test order must include every test in the current bot")
        by_id = {record.id: record for record in records}
        for order, test_id in enumerate(test_ids):
            by_id[test_id].order = order
        self._session.flush()
        return [_definition(by_id[test_id]) for test_id in test_ids]

    def seed_published_test(
        self,
        *,
        bot_instance_id: int,
        slug: str,
        name: str,
        intro_text: str | None,
        schema: dict,
        is_active: bool,
    ) -> PublishedTest:
        """One-shot create+draft+publish for a test authored outside the (not-yet-built) admin
        constructor -- see Task 068's Non-goals. Not exposed over HTTP; called only from a CLI
        seed script."""
        definition_record = TestDefinitionRecord(
            bot_instance_id=bot_instance_id,
            slug=slug,
            is_active=is_active,
            name=name,
            last_published_revision=0,
        )
        self._session.add(definition_record)
        self._session.flush()

        draft_record = TestDraftRecord(
            test_definition_id=definition_record.id,
            name=name,
            intro_text=intro_text,
            schema=schema,
            revision=0,
        )
        self._session.add(draft_record)

        version_record = TestVersionRecord(
            test_definition_id=definition_record.id,
            version=1,
            source_revision=0,
            name=name,
            intro_text=intro_text,
            schema=schema,
            published_at=datetime.now(tz=UTC),
        )
        self._session.add(version_record)
        self._session.flush()

        definition_record.published_version_id = version_record.id
        self._session.flush()
        return PublishedTest(definition=_definition(definition_record), version=_version(version_record))

    def get_attempt(self, bot_instance_id: int, attempt_id: int) -> TestAttempt | None:
        record = self._session.execute(
            select(TestAttemptRecord).where(
                TestAttemptRecord.bot_instance_id == bot_instance_id,
                TestAttemptRecord.id == attempt_id,
            )
        ).scalar_one_or_none()
        return _attempt(record) if record else None

    def get_attempt_for_version(
        self, bot_instance_id: int, user_id: int, test_version_id: int
    ) -> TestAttempt | None:
        # A retake (Task 075) can leave more than one attempt for the same (user, version) --
        # the most recently started one is the one to resume/return/retake-from.
        record = self._session.execute(
            select(TestAttemptRecord)
            .where(
                TestAttemptRecord.bot_instance_id == bot_instance_id,
                TestAttemptRecord.user_id == user_id,
                TestAttemptRecord.test_version_id == test_version_id,
            )
            .order_by(TestAttemptRecord.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return _attempt(record) if record else None

    def delete_stale_in_progress_attempts(
        self, bot_instance_id: int, user_id: int, test_definition_id: int
    ) -> None:
        # A republish between the student's last visit and this one supersedes whatever version
        # any of their in-progress attempts on this test point at -- `get_attempt_for_version`
        # only ever resolves the *current* published version, so a stale row would otherwise never
        # be found, resumed, or completed again and would linger forever as a duplicate
        # "in progress" tile in `list_attempts_for_user` (Task 070's history block). Only called
        # from `StartOrResumeAttempt` once it has already confirmed no attempt exists for the
        # current version, so every row this touches necessarily belongs to a superseded one and
        # holds no submitted result -- just an abandoned draft against a schema that no longer
        # exists.
        self._session.execute(
            delete(TestAttemptRecord).where(
                TestAttemptRecord.bot_instance_id == bot_instance_id,
                TestAttemptRecord.user_id == user_id,
                TestAttemptRecord.test_definition_id == test_definition_id,
                TestAttemptRecord.status == TestAttemptStatus.IN_PROGRESS,
            )
        )

    def create_attempt(
        self,
        *,
        bot_instance_id: int,
        test_definition_id: int,
        test_version_id: int,
        user_id: int,
    ) -> TestAttempt:
        record = TestAttemptRecord(
            bot_instance_id=bot_instance_id,
            test_definition_id=test_definition_id,
            test_version_id=test_version_id,
            user_id=user_id,
            status=TestAttemptStatus.IN_PROGRESS,
            answers={},
            started_at=datetime.now(tz=UTC),
        )
        self._session.add(record)
        self._session.flush()
        return _attempt(record)

    def save_attempt_answers(self, attempt_id: int, answers: dict) -> TestAttempt:
        record = self._session.execute(
            select(TestAttemptRecord).where(TestAttemptRecord.id == attempt_id).with_for_update()
        ).scalar_one()
        record.answers = {**record.answers, **answers}
        self._session.flush()
        return _attempt(record)

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
        record = self._session.execute(
            select(TestAttemptRecord).where(TestAttemptRecord.id == attempt_id).with_for_update()
        ).scalar_one()
        now = datetime.now(tz=UTC)
        record.answers = answers
        record.computed_results = computed_results
        record.rendered_result_text = rendered_result_text
        record.status = TestAttemptStatus.COMPLETED
        record.completed_at = now
        record.consent_accepted = consent_accepted
        record.consent_accepted_at = now if consent_accepted else None
        record.identity_snapshot = identity_snapshot
        self._session.flush()
        return _attempt(record)

    def list_attempts_for_user(self, bot_instance_id: int, user_id: int) -> list[TestAttempt]:
        # Task 075: only ever surfaces an attempt whose own (frozen, per-version) history-visibility
        # flag is on, read straight off the attempt's own `TestVersionRecord`, never the test's
        # current draft, so an admin changing the setting later never retroactively changes
        # whether an already-taken attempt appears in this list. `computed_results` stays
        # truthful here regardless of `show_scores` -- that redaction happens only at the
        # presentation layer (`_attempt_out`), never in this repository.
        records = self._session.execute(
            select(TestAttemptRecord)
            .join(TestVersionRecord, TestVersionRecord.id == TestAttemptRecord.test_version_id)
            .where(
                TestAttemptRecord.bot_instance_id == bot_instance_id,
                TestAttemptRecord.user_id == user_id,
                TestVersionRecord.show_attempt_history.is_(True),
            )
            .order_by(TestAttemptRecord.started_at.desc())
        ).scalars()
        return [_attempt(record) for record in records]

    def list_attempts_for_test(
        self,
        bot_instance_id: int,
        test_definition_id: int,
        *,
        status: TestAttemptStatus | None = None,
    ) -> list[TestAttempt]:
        query = select(TestAttemptRecord).where(
            TestAttemptRecord.bot_instance_id == bot_instance_id,
            TestAttemptRecord.test_definition_id == test_definition_id,
        )
        if status is not None:
            query = query.where(TestAttemptRecord.status == status)
        records = self._session.execute(query.order_by(TestAttemptRecord.started_at.desc())).scalars()
        return [_attempt(record) for record in records]

    # --- Consent documents (Task 073) -----------------------------------------------------------

    def list_consent_documents(self, bot_instance_id: int) -> list[ConsentDocument]:
        records = self._session.execute(
            select(ConsentDocumentRecord)
            .where(ConsentDocumentRecord.bot_instance_id == bot_instance_id)
            .order_by(ConsentDocumentRecord.updated_at.desc())
        ).scalars()
        return [_consent_document(record) for record in records]

    def get_consent_document(self, bot_instance_id: int, document_id: int) -> ConsentDocument | None:
        record = self._session.execute(
            select(ConsentDocumentRecord).where(
                ConsentDocumentRecord.bot_instance_id == bot_instance_id,
                ConsentDocumentRecord.id == document_id,
            )
        ).scalar_one_or_none()
        return _consent_document(record) if record else None

    def create_consent_document(self, document: ConsentDocument) -> ConsentDocument:
        record = ConsentDocumentRecord(
            bot_instance_id=document.bot_instance_id,
            title=document.title,
            body_html=document.body_html,
            created_by=document.created_by,
            updated_by=document.updated_by,
        )
        self._session.add(record)
        self._session.flush()
        return _consent_document(record)

    def update_consent_document(
        self,
        bot_instance_id: int,
        document_id: int,
        *,
        title: str,
        body_html: str,
        updated_by: int | None,
    ) -> ConsentDocument | None:
        record = self._session.execute(
            select(ConsentDocumentRecord).where(
                ConsentDocumentRecord.bot_instance_id == bot_instance_id,
                ConsentDocumentRecord.id == document_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return None
        record.title = title
        record.body_html = body_html
        record.updated_by = updated_by
        self._session.flush()
        return _consent_document(record)

    def delete_consent_document(self, bot_instance_id: int, document_id: int) -> bool:
        record = self._session.execute(
            select(ConsentDocumentRecord).where(
                ConsentDocumentRecord.bot_instance_id == bot_instance_id,
                ConsentDocumentRecord.id == document_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return False
        self._session.delete(record)
        self._session.flush()
        return True
