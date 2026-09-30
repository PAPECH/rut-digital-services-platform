from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, slots=True)
class TestDefinition:
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    id: int | None
    bot_instance_id: int
    slug: str
    name: str = ""
    order: int = 0
    is_active: bool = False
    is_archived: bool = False
    published_version_id: int | None = None
    last_published_revision: int = -1


@dataclass(frozen=True, slots=True)
class TestDraft:
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    test_definition_id: int
    name: str
    intro_text: str | None = None
    schema: dict[str, Any] = field(default_factory=dict)
    revision: int = 0
    updated_at: datetime | None = None
    # Participation-consent checkbox (Task 073): `consent_document_id` is a *live* reference into
    # this bot's `ConsentDocument` library, re-resolved on every read/edit while the test is still
    # a draft -- contrast with `TestVersion.consent_document_title`/`consent_document_body_html`
    # below, which are a frozen copy taken at publish time.
    consent_enabled: bool = False
    consent_document_id: int | None = None
    consent_checkbox_text: str | None = None
    # Per-test attempt settings (Task 075): independent of each other and of consent above.
    allow_retake: bool = False
    show_attempt_history: bool = True
    show_scores: bool = False


@dataclass(frozen=True, slots=True)
class TestVersion:
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    id: int | None
    test_definition_id: int
    version: int
    source_revision: int
    name: str
    intro_text: str | None
    schema: dict[str, Any]
    published_by: int | None
    published_at: datetime
    # Frozen copy of the referenced `ConsentDocument`'s content at the moment this version was
    # published (Task 073) -- deliberately not a live reference (no `consent_document_id` here):
    # editing or deleting the source document must never change what an already-published version
    # shows, mirroring how `schema` itself is a frozen copy of the draft's, not a live pointer.
    consent_enabled: bool = False
    consent_document_title: str | None = None
    consent_document_body_html: str | None = None
    consent_checkbox_text: str | None = None
    # Frozen copy of the draft's attempt settings at publish time (Task 075) -- same "copy, not
    # live reference" discipline as everything else on this entity.
    allow_retake: bool = False
    show_attempt_history: bool = True
    show_scores: bool = False


@dataclass(frozen=True, slots=True)
class ConsentDocument:
    """Admin-authored, freely created/edited/deleted per-bot library entry (Task 073) -- title +
    trusted HTML content, referenced by a `TestDraft`/frozen into a `TestVersion` via the fields
    above. Not itself draft/version-tracked: what must stay immutable once published is the test
    version's own frozen copy, not this row's edit history."""

    id: int | None
    bot_instance_id: int
    title: str
    body_html: str
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublishedTest:
    definition: TestDefinition
    version: TestVersion


class TestAttemptStatus(StrEnum):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class TestAttempt:
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    id: int | None
    bot_instance_id: int
    test_definition_id: int
    test_version_id: int
    user_id: int
    status: TestAttemptStatus
    answers: dict[str, Any] = field(default_factory=dict)
    computed_results: dict[str, dict[str, Any]] | None = None
    rendered_result_text: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    consent_accepted: bool = False
    consent_accepted_at: datetime | None = None
    # Frozen once, at completion, from the student's shared profile (Task 080) -- last_name/
    # first_name/patronymic/birth_date/email, `birth_date` as an ISO date string. `None` for
    # every attempt completed before this shipped and for one completed without a resolvable
    # profile; export falls back to a live profile lookup in that case (`xlsx_export.py`).
    identity_snapshot: dict[str, Any] | None = None
