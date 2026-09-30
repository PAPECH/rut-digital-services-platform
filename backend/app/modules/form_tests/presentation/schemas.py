from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _student_safe_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip each option's `score` before this reaches a student -- the plan's own contract
    ("no scoring internals leaked to the client") extends beyond `result_scales`/`filters`/
    `result_template` to the option weights themselves, which could otherwise reveal how an
    instrument like Beck depression is scored from the network response alone."""
    safe: list[dict[str, Any]] = []
    for element in elements:
        if "options" not in element:
            safe.append(element)
            continue
        safe.append(
            {
                **element,
                "options": [
                    {"value": option["value"], "label": option["label"]} for option in element["options"]
                ],
            }
        )
    return safe


class PublishedTestSummary(StrictModel):
    id: int
    slug: str
    name: str
    version_id: int
    version: int


class PublishedTestDetail(PublishedTestSummary):
    intro_text: str | None
    elements: list[dict[str, Any]]
    consent_enabled: bool
    consent_checkbox_text: str | None
    consent_document_title: str | None
    allow_retake: bool
    # Result-scale key -> human label, present only when `show_scores` is on for this version --
    # never terms/weights/constant/aggregation (same "no scoring internals leaked" contract
    # `_student_safe_elements` already enforces for element option scores). Lets a result screen
    # show "Дистресс: 10" instead of the raw scale key when scores are visible; when scores are
    # off there is nothing for a student to label, so this stays `None` symmetrically.
    result_scale_labels: dict[str, str] | None

    @classmethod
    def from_schema(
        cls,
        *,
        id: int,
        slug: str,
        name: str,
        intro_text: str | None,
        version_id: int,
        version: int,
        elements: list[dict[str, Any]],
        consent_enabled: bool = False,
        consent_checkbox_text: str | None = None,
        consent_document_title: str | None = None,
        allow_retake: bool = False,
        show_scores: bool = False,
        result_scales: list[dict[str, Any]] | None = None,
    ) -> PublishedTestDetail:
        return cls(
            id=id,
            slug=slug,
            name=name,
            version_id=version_id,
            version=version,
            intro_text=intro_text,
            elements=_student_safe_elements(elements),
            consent_enabled=consent_enabled,
            consent_checkbox_text=consent_checkbox_text,
            consent_document_title=consent_document_title,
            allow_retake=allow_retake,
            result_scale_labels=(
                {scale["key"]: scale["label"] for scale in (result_scales or [])} if show_scores else None
            ),
        )


class ConsentDocumentContentOut(StrictModel):
    title: str
    body_html: str


class AttemptOut(StrictModel):
    id: int
    test_definition_id: int
    test_version_id: int
    status: str
    answers: dict[str, Any]
    computed_results: dict[str, Any] | None
    rendered_result_text: str | None
    started_at: datetime
    completed_at: datetime | None
    consent_accepted: bool
    consent_accepted_at: datetime | None


class AutosaveAttemptRequest(StrictModel):
    answers: dict[str, Any]


class StartAttemptRequest(StrictModel):
    pass


class CompleteAttemptRequest(StrictModel):
    consent_accepted: bool = False


# --- Admin ------------------------------------------------------------------------------------


class AdminTestSummary(StrictModel):
    id: int
    slug: str
    name: str
    order: int
    is_active: bool
    is_archived: bool
    published_version_id: int | None
    last_published_revision: int


class AdminTestDetail(AdminTestSummary):
    intro_text: str | None
    test_schema: dict[str, Any]
    consent_enabled: bool
    consent_document_title: str | None
    consent_checkbox_text: str | None
    allow_retake: bool
    show_attempt_history: bool
    show_scores: bool


class UpdateTestRequest(StrictModel):
    is_active: bool | None = None
    is_archived: bool | None = None


class AttemptSubmitterOut(StrictModel):
    """Trimmed user summary for the admin results view's clickable profile link (Task 077) --
    deliberately not the full `forms`' `SubmitterOut` PII set (no birth date/phone/email/study
    group): this module only needs enough to render a name + avatar that opens `UserCardPanel`,
    which re-fetches the full card itself. Duplicated here rather than imported from
    `modules.forms` -- one business module's presentation schema is not another's dependency."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    username: str | None = None
    photo_url: str | None = None


class AdminAttemptSummary(StrictModel):
    id: int
    user_id: int
    submitter: AttemptSubmitterOut | None = None
    answers: dict[str, Any]
    # Present on the list endpoint too, not just the detail one (Task 077): the wide-table results
    # view needs every attempt's scale values at once to render its scale columns, without an
    # extra detail fetch per row.
    computed_results: dict[str, Any] | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    consent_accepted: bool
    consent_accepted_at: datetime | None


class AdminAttemptDetail(AdminAttemptSummary):
    rendered_result_text: str | None


# --- Admin constructor (Task 069) --------------------------------------------------------------


class TestCreateRequest(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    name: str = Field(min_length=1, max_length=300)
    order: int = Field(default=0, ge=0, le=100_000)


class TestReorderRequest(StrictModel):
    test_ids: list[PositiveInt] = Field(max_length=500)


class TestDraftResponse(StrictModel):
    test_id: int
    name: str
    intro_text: str | None
    test_schema: dict[str, Any]
    revision: int
    updated_at: datetime | None
    consent_enabled: bool
    consent_document_id: int | None
    consent_document_title: str | None
    consent_document_missing: bool
    consent_checkbox_text: str | None
    allow_retake: bool
    show_attempt_history: bool
    show_scores: bool


class TestDraftSaveRequest(StrictModel):
    expected_revision: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)
    intro_text: str | None = Field(default=None, max_length=10_000)
    test_schema: dict[str, Any]
    consent_enabled: bool = False
    consent_document_id: int | None = None
    consent_checkbox_text: str | None = Field(default=None, max_length=2000)
    allow_retake: bool = False
    show_attempt_history: bool = True
    show_scores: bool = False


class TestPublishRequest(StrictModel):
    expected_revision: int = Field(ge=0)


class TestPreviewRequest(StrictModel):
    filters: list[dict[str, Any]]
    result_template: str = Field(max_length=50_000)
    sample_values: dict[str, float]


class TestPreviewResponse(StrictModel):
    rendered_text: str
    chunks: list[str]


class TestSchemaExportResponse(StrictModel):
    name: str
    intro_text: str | None
    test_schema: dict[str, Any]


# --- Consent documents (Task 073) --------------------------------------------------------------


class AdminConsentDocumentSummary(StrictModel):
    id: int
    title: str
    updated_at: datetime | None


class AdminConsentDocumentDetail(AdminConsentDocumentSummary):
    body_html: str
    created_at: datetime | None


class ConsentDocumentSaveRequest(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    body_html: str = Field(min_length=1, max_length=200_000)
