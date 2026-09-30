from __future__ import annotations

from typing import Protocol

from .entities import (
    ConsentDocument,
    PublishedTest,
    TestAttempt,
    TestAttemptStatus,
    TestDefinition,
    TestDraft,
)


class TestRepository(Protocol):
    def list_tests(self, bot_instance_id: int) -> list[TestDefinition]: ...

    def list_active_published(self, bot_instance_id: int) -> list[PublishedTest]: ...

    def get_test(self, bot_instance_id: int, test_id: int) -> TestDefinition | None: ...

    def get_test_by_slug(self, bot_instance_id: int, slug: str) -> TestDefinition | None: ...

    def get_published(self, bot_instance_id: int, test_id: int) -> PublishedTest | None: ...

    def get_version(self, bot_instance_id: int, test_id: int, version_id: int) -> PublishedTest | None: ...

    def get_draft(self, bot_instance_id: int, test_id: int) -> TestDraft | None: ...

    def update_test(self, definition: TestDefinition) -> TestDefinition: ...

    def create_test(
        self,
        definition: TestDefinition,
        draft: TestDraft,
        *,
        created_by: int | None,
    ) -> tuple[TestDefinition, TestDraft]: ...

    def save_draft(
        self,
        bot_instance_id: int,
        draft: TestDraft,
        *,
        expected_revision: int,
        updated_by: int | None,
    ) -> TestDraft: ...

    def publish(
        self,
        bot_instance_id: int,
        test_id: int,
        *,
        expected_revision: int,
        published_by: int | None,
    ) -> PublishedTest: ...

    def reorder(self, bot_instance_id: int, test_ids: list[int]) -> list[TestDefinition]: ...

    def seed_published_test(
        self,
        *,
        bot_instance_id: int,
        slug: str,
        name: str,
        intro_text: str | None,
        schema: dict,
        is_active: bool,
    ) -> PublishedTest: ...

    def get_attempt(self, bot_instance_id: int, attempt_id: int) -> TestAttempt | None: ...

    def get_attempt_for_version(
        self, bot_instance_id: int, user_id: int, test_version_id: int
    ) -> TestAttempt | None: ...

    def delete_stale_in_progress_attempts(
        self, bot_instance_id: int, user_id: int, test_definition_id: int
    ) -> None: ...

    def create_attempt(
        self,
        *,
        bot_instance_id: int,
        test_definition_id: int,
        test_version_id: int,
        user_id: int,
    ) -> TestAttempt: ...

    def save_attempt_answers(self, attempt_id: int, answers: dict) -> TestAttempt: ...

    def complete_attempt(
        self,
        attempt_id: int,
        *,
        answers: dict,
        computed_results: dict,
        rendered_result_text: str,
        consent_accepted: bool = False,
        identity_snapshot: dict | None = None,
    ) -> TestAttempt: ...

    def list_attempts_for_user(self, bot_instance_id: int, user_id: int) -> list[TestAttempt]: ...

    def list_attempts_for_test(
        self,
        bot_instance_id: int,
        test_definition_id: int,
        *,
        status: TestAttemptStatus | None = None,
    ) -> list[TestAttempt]: ...

    # --- Consent documents (Task 073) ------------------------------------------------------

    def list_consent_documents(self, bot_instance_id: int) -> list[ConsentDocument]: ...

    def get_consent_document(self, bot_instance_id: int, document_id: int) -> ConsentDocument | None: ...

    def create_consent_document(self, document: ConsentDocument) -> ConsentDocument: ...

    def update_consent_document(
        self,
        bot_instance_id: int,
        document_id: int,
        *,
        title: str,
        body_html: str,
        updated_by: int | None,
    ) -> ConsentDocument | None: ...

    def delete_consent_document(self, bot_instance_id: int, document_id: int) -> bool: ...
