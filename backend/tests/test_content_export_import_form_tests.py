from __future__ import annotations

import pytest

from app.cli.content_export_import.archive import ContentExportImportError
from app.cli.content_export_import.form_tests import remap_consent_document_id


def test_consent_document_id_is_remapped() -> None:
    assert remap_consent_document_id(7, {7: 107}) == 107


def test_null_consent_document_id_stays_null() -> None:
    assert remap_consent_document_id(None, {7: 107}) is None


def test_missing_consent_document_id_is_rejected() -> None:
    with pytest.raises(ContentExportImportError, match="missing from archive"):
        remap_consent_document_id(8, {7: 107})
