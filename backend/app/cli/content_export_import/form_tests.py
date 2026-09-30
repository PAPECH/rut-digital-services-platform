from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modules.form_tests.infrastructure.models import (
    ConsentDocumentRecord,
    TestDefinitionRecord,
    TestDraftRecord,
    TestVersionRecord,
)
from .archive import ContentExportImportError


def export_consent_documents(session: Session, bot_id: int) -> list[dict[str, Any]]:
    records = session.execute(
        select(ConsentDocumentRecord).where(ConsentDocumentRecord.bot_instance_id == bot_id)
    ).scalars().all()
    return [
        {"id": record.id, "title": record.title, "body_html": record.body_html}
        for record in records
    ]


def export_tests(session: Session, bot_id: int) -> list[dict[str, Any]]:
    definitions = session.execute(
        select(TestDefinitionRecord).where(TestDefinitionRecord.bot_instance_id == bot_id)
    ).scalars().all()
    result: list[dict[str, Any]] = []
    for definition in definitions:
        draft = session.execute(
            select(TestDraftRecord).where(
                TestDraftRecord.test_definition_id == definition.id
            )
        ).scalar_one()
        published = None
        if definition.published_version_id is not None:
            version = session.get(TestVersionRecord, definition.published_version_id)
            assert version is not None
            published = {
                "name": version.name,
                "intro_text": version.intro_text,
                "schema": deepcopy(version.schema),
                "consent_enabled": version.consent_enabled,
                "consent_document_title": version.consent_document_title,
                "consent_document_body_html": version.consent_document_body_html,
                "consent_checkbox_text": version.consent_checkbox_text,
                "allow_retake": version.allow_retake,
                "show_attempt_history": version.show_attempt_history,
                "show_scores": version.show_scores,
            }
        result.append(
            {
                "id": definition.id,
                "slug": definition.slug,
                "name": definition.name,
                "order": definition.order,
                "is_active": definition.is_active,
                "is_archived": definition.is_archived,
                "draft": {
                    "name": draft.name,
                    "intro_text": draft.intro_text,
                    "schema": deepcopy(draft.schema),
                    "consent_enabled": draft.consent_enabled,
                    "consent_document_id": draft.consent_document_id,
                    "consent_checkbox_text": draft.consent_checkbox_text,
                    "allow_retake": draft.allow_retake,
                    "show_attempt_history": draft.show_attempt_history,
                    "show_scores": draft.show_scores,
                },
                "published": published,
            }
        )
    return result


def guard_target_empty(session: Session, bot_id: int) -> None:
    has_test = session.execute(
        select(TestDefinitionRecord.id)
        .where(TestDefinitionRecord.bot_instance_id == bot_id)
        .limit(1)
    ).scalar_one_or_none()
    has_consent = session.execute(
        select(ConsentDocumentRecord.id)
        .where(ConsentDocumentRecord.bot_instance_id == bot_id)
        .limit(1)
    ).scalar_one_or_none()
    if has_test is not None or has_consent is not None:
        raise ContentExportImportError(
            "target bot already has tests or consent documents -- refusing to import tests"
        )


def validate_consent_references(manifest: dict[str, Any]) -> None:
    available = {int(document["id"]) for document in manifest["consent_documents"]}
    missing: set[int] = set()
    for test in manifest["tests"]:
        source_id = test["draft"].get("consent_document_id")
        if source_id is not None and int(source_id) not in available:
            missing.add(int(source_id))
    if missing:
        raise ContentExportImportError(
            "tests reference consent document(s) missing from archive: "
            + ", ".join(str(value) for value in sorted(missing))
        )


def import_consent_documents(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for document in manifest["consent_documents"]:
        record = ConsentDocumentRecord(
            bot_instance_id=bot_id,
            title=document["title"],
            body_html=document["body_html"],
            created_by=None,
            updated_by=None,
        )
        session.add(record)
        session.flush()
        mapping[int(document["id"])] = record.id
    return mapping


def remap_consent_document_id(
    source_id: int | None,
    consent_id_map: dict[int, int],
) -> int | None:
    """Resolve a draft's archive-local consent id without leaking source ids."""

    if source_id is None:
        return None
    try:
        return consent_id_map[int(source_id)]
    except KeyError as exc:
        raise ContentExportImportError(
            f"test draft references consent document missing from archive: {source_id}"
        ) from exc


def import_tests(
    session: Session,
    manifest: dict[str, Any],
    bot_id: int,
    consent_id_map: dict[int, int],
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for test in manifest["tests"]:
        draft = test["draft"]
        published = test["published"]
        has_published = published is not None
        definition = TestDefinitionRecord(
            bot_instance_id=bot_id,
            slug=test["slug"],
            order=test["order"],
            is_active=test["is_active"],
            is_archived=test["is_archived"],
            last_published_revision=0 if has_published else -1,
            name=test["name"],
            created_by=None,
        )
        session.add(definition)
        session.flush()

        source_consent_id = draft.get("consent_document_id")
        draft_record = TestDraftRecord(
            test_definition_id=definition.id,
            name=draft["name"],
            intro_text=draft["intro_text"],
            schema=deepcopy(draft["schema"]),
            revision=1 if has_published else 0,
            updated_by=None,
            consent_enabled=draft["consent_enabled"],
            consent_document_id=remap_consent_document_id(
                source_consent_id,
                consent_id_map,
            ),
            consent_checkbox_text=draft["consent_checkbox_text"],
            allow_retake=draft["allow_retake"],
            show_attempt_history=draft["show_attempt_history"],
            show_scores=draft["show_scores"],
        )
        session.add(draft_record)
        session.flush()

        if has_published:
            version = TestVersionRecord(
                test_definition_id=definition.id,
                version=1,
                source_revision=0,
                name=published["name"],
                intro_text=published["intro_text"],
                schema=deepcopy(published["schema"]),
                published_by=None,
                published_at=datetime.now(tz=UTC),
                consent_enabled=published["consent_enabled"],
                consent_document_title=published["consent_document_title"],
                consent_document_body_html=published["consent_document_body_html"],
                consent_checkbox_text=published["consent_checkbox_text"],
                allow_retake=published["allow_retake"],
                show_attempt_history=published["show_attempt_history"],
                show_scores=published["show_scores"],
            )
            session.add(version)
            session.flush()
            definition.published_version_id = version.id
            session.flush()

        mapping[int(test["id"])] = definition.id
    return mapping
