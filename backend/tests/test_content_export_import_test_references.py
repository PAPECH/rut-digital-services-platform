from __future__ import annotations

import pytest

from app.cli.content_export_import.archive import ContentExportImportError
from app.cli.content_export_import.form_test_references import (
    collect_referenced_test_ids,
    finalize_test_id_mapping,
    resolve_test_reference_plan,
)


def _archive_tests() -> list[dict]:
    return [
        {"id": 4, "slug": "wellbeing"},
        {"id": 7, "slug": "motivation"},
    ]


def test_archive_test_import_mapping_wins() -> None:
    plan = resolve_test_reference_plan(
        {4},
        _archive_tests(),
        tests_selected=True,
        existing_target_ids_by_slug={"wellbeing": 99},
    )

    assert finalize_test_id_mapping(plan, {4: 404}) == {4: 404}


def test_content_only_import_resolves_existing_target_test_by_slug() -> None:
    plan = resolve_test_reference_plan(
        {4},
        _archive_tests(),
        tests_selected=False,
        existing_target_ids_by_slug={"wellbeing": 404},
    )

    assert finalize_test_id_mapping(plan, {}) == {4: 404}


def test_unresolved_references_list_every_slug() -> None:
    with pytest.raises(ContentExportImportError) as exc_info:
        resolve_test_reference_plan(
            {4, 7},
            _archive_tests(),
            tests_selected=False,
            existing_target_ids_by_slug={},
        )

    message = str(exc_info.value)
    assert "wellbeing" in message
    assert "motivation" in message


def test_reference_to_test_missing_from_archive_lists_source_id() -> None:
    with pytest.raises(ContentExportImportError, match="source-id:12"):
        resolve_test_reference_plan(
            {12},
            _archive_tests(),
            tests_selected=True,
            existing_target_ids_by_slug={},
        )


def test_collect_referenced_test_ids_including_nested_tabs() -> None:
    categories = [
        {
            "draft": {
                "blocks": [
                    {"id": "a", "type": "test_action", "test_id": 4},
                    {
                        "id": "tabs",
                        "type": "tabs",
                        "tabs": [
                            {
                                "key": "one",
                                "title": "One",
                                "blocks": [
                                    {"id": "b", "type": "test_action", "test_id": 7}
                                ],
                            }
                        ],
                    },
                ]
            },
            "published": None,
        }
    ]

    assert collect_referenced_test_ids(categories) == {4, 7}
