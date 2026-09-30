from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modules.content.domain.blocks import extract_test_references
from ...modules.form_tests.infrastructure.models import TestDefinitionRecord
from .archive import ContentExportImportError


@dataclass(frozen=True)
class TestReferencePlan:
    referenced_source_ids: frozenset[int]
    source_slug_by_id: dict[int, str]
    existing_target_id_by_source_id: dict[int, int]


def collect_referenced_test_ids(categories: list[dict[str, Any]]) -> set[int]:
    referenced: set[int] = set()
    for category in categories:
        for section in (category.get("draft"), category.get("published")):
            if section is not None:
                referenced.update(extract_test_references(section["blocks"]))
    return referenced


def resolve_test_reference_plan(
    referenced_source_ids: set[int],
    archive_tests: list[dict[str, Any]],
    *,
    tests_selected: bool,
    existing_target_ids_by_slug: dict[str, int],
) -> TestReferencePlan:
    source_slug_by_id = {int(test["id"]): str(test["slug"]) for test in archive_tests}
    existing_mapping: dict[int, int] = {}
    unresolved: list[str] = []

    for source_id in sorted(referenced_source_ids):
        slug = source_slug_by_id.get(source_id)
        if slug is None:
            unresolved.append(f"source-id:{source_id}")
            continue
        if tests_selected:
            continue
        target_id = existing_target_ids_by_slug.get(slug)
        if target_id is None:
            unresolved.append(slug)
        else:
            existing_mapping[source_id] = target_id

    if unresolved:
        raise ContentExportImportError(
            "content has unresolved test reference(s): " + ", ".join(unresolved)
        )

    return TestReferencePlan(
        referenced_source_ids=frozenset(referenced_source_ids),
        source_slug_by_id=source_slug_by_id,
        existing_target_id_by_source_id=existing_mapping,
    )


def existing_target_test_ids_by_slug(
    session: Session,
    bot_id: int,
    slugs: set[str],
) -> dict[str, int]:
    if not slugs:
        return {}
    rows = session.execute(
        select(TestDefinitionRecord.slug, TestDefinitionRecord.id).where(
            TestDefinitionRecord.bot_instance_id == bot_id,
            TestDefinitionRecord.slug.in_(slugs),
        )
    ).all()
    return {row.slug: row.id for row in rows}


def finalize_test_id_mapping(
    plan: TestReferencePlan,
    imported_test_ids: dict[int, int],
) -> dict[int, int]:
    mapping = dict(plan.existing_target_id_by_source_id)
    mapping.update(imported_test_ids)
    missing = plan.referenced_source_ids - mapping.keys()
    if missing:
        labels = [plan.source_slug_by_id.get(value, f"source-id:{value}") for value in sorted(missing)]
        raise ContentExportImportError(
            "content has unresolved test reference(s): " + ", ".join(labels)
        )
    return mapping
