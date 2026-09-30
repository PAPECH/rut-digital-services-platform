"""cli/import_legacy.py's ai_classification mapping (Task 051).

The importer never brings in a legacy bot's own kb_documents, so an old
kb:{id}/kb_selected:{id}-shaped value has no meaningful target-side document to
point at — it must land in legacy_unknown, not be parsed for an id.
"""

from __future__ import annotations

from app.cli.import_legacy import _ai_classification
from app.modules.knowledge_base.domain.entities import MessageAiClassificationEnum


def test_none_stays_none() -> None:
    assert _ai_classification(None) is None


def test_exact_match_is_kept() -> None:
    assert _ai_classification("certificate") == MessageAiClassificationEnum.certificate
    assert _ai_classification("kb_no_match") == MessageAiClassificationEnum.kb_no_match


def test_old_id_suffixed_values_bucket_to_legacy_unknown() -> None:
    assert _ai_classification("kb:42") == MessageAiClassificationEnum.legacy_unknown
    assert _ai_classification("kb_selected:7") == MessageAiClassificationEnum.legacy_unknown


def test_unrecognized_garbage_bucket_to_legacy_unknown() -> None:
    assert _ai_classification("some legacy freeform note") == MessageAiClassificationEnum.legacy_unknown
