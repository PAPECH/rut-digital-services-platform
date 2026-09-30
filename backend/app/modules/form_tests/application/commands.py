from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class UpdateTestCommand:
    bot_instance_id: int
    test_id: int
    is_active: bool | None = None
    is_archived: bool | None = None


@dataclass(frozen=True, slots=True)
class CreateTestCommand:
    bot_instance_id: int
    slug: str
    name: str
    order: int
    created_by: int | None


@dataclass(frozen=True, slots=True)
class SaveTestDraftCommand:
    bot_instance_id: int
    test_id: int
    expected_revision: int
    name: str
    intro_text: str | None
    schema: dict[str, Any]
    updated_by: int | None
    consent_enabled: bool = False
    consent_document_id: int | None = None
    consent_checkbox_text: str | None = None
    allow_retake: bool = False
    show_attempt_history: bool = True
    show_scores: bool = False


@dataclass(frozen=True, slots=True)
class PublishTestCommand:
    bot_instance_id: int
    test_id: int
    expected_revision: int
    published_by: int | None


@dataclass(frozen=True, slots=True)
class PreviewTestResultCommand:
    filters: list[dict[str, Any]]
    result_template: str
    sample_values: dict[str, float]


@dataclass(frozen=True, slots=True)
class AutosaveAttemptCommand:
    bot_instance_id: int
    user_id: int
    attempt_id: int
    answers: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CompleteAttemptCommand:
    bot_instance_id: int
    user_id: int
    attempt_id: int
    consent_accepted: bool = False


@dataclass(frozen=True, slots=True)
class CreateConsentDocumentCommand:
    bot_instance_id: int
    title: str
    body_html: str
    created_by: int | None


@dataclass(frozen=True, slots=True)
class UpdateConsentDocumentCommand:
    bot_instance_id: int
    document_id: int
    title: str
    body_html: str
    updated_by: int | None
