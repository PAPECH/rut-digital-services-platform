from __future__ import annotations

import pytest

from app.cli.content_export_import.archive import (
    FORMAT_VERSION,
    ContentExportImportError,
    normalize_manifest,
    parse_only_parts,
)


def _v2_manifest() -> dict:
    return {
        "format_version": 2,
        "source_bot": {"id": 1, "slug": "source", "name": "Source"},
        "counts": {"categories": 0, "forms": 0, "attachments": 0},
        "categories": [],
        "forms": [],
        "attachments": [],
    }


def test_v2_manifest_is_normalized_as_content_only() -> None:
    normalized = normalize_manifest(_v2_manifest())

    assert normalized["format_version"] == FORMAT_VERSION
    assert normalized["parts"] == ["content"]
    assert normalized["tests"] == []
    assert normalized["consent_documents"] == []
    assert normalized["kb_faq"] == []
    assert normalized["kb_documents"] == []
    assert normalized["counts"]["tests"] == 0


def test_unknown_archive_version_is_rejected() -> None:
    manifest = _v2_manifest()
    manifest["format_version"] = 99

    with pytest.raises(ContentExportImportError, match="unsupported archive"):
        normalize_manifest(manifest)


def test_parse_only_defaults_to_parts_in_canonical_order() -> None:
    assert parse_only_parts(None, ["kb", "content", "tests"]) == (
        "content",
        "tests",
        "kb",
    )


def test_parse_only_rejects_unknown_part() -> None:
    with pytest.raises(ContentExportImportError, match="unknown --only"):
        parse_only_parts("content,users", ["content", "tests", "kb"])


def test_parse_only_rejects_part_missing_from_archive() -> None:
    with pytest.raises(ContentExportImportError, match="does not contain"):
        parse_only_parts("tests", ["content"])
