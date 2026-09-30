from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from app.modules.content.presentation.schemas import ContentBlock

_block_adapter: TypeAdapter = TypeAdapter(list[ContentBlock])


def test_paragraph_block_schema_accepts_legacy_plain_string() -> None:
    blocks = _block_adapter.validate_python([{"id": "p1", "type": "paragraph", "text": "hello"}])
    assert blocks[0].text == "hello"


def test_paragraph_block_schema_accepts_rich_text_document() -> None:
    """Regression test: the Pydantic request/response schema must accept the same rich-text
    shape the domain validator (content_blocks.domain.rich_text) accepts -- this was missing
    initially (Task 040 shipped the domain-layer change but not this schema), so a WYSIWYG-edited
    paragraph would have been rejected with a 422 before ever reaching the domain layer."""
    rich_text = {
        "format": "rich_text_v1",
        "nodes": [
            {
                "type": "paragraph",
                "runs": [{"text": "bold", "marks": ["bold"], "href": None}],
            },
            {
                "type": "bullet_list",
                "items": [[{"text": "item", "marks": [], "href": None}]],
            },
        ],
    }
    blocks = _block_adapter.validate_python(
        [{"id": "p1", "type": "paragraph", "text": rich_text}]
    )
    assert blocks[0].text.format == "rich_text_v1"
    assert blocks[0].text.nodes[0].runs[0].marks == ["bold"]


def test_callout_block_schema_accepts_rich_text_document() -> None:
    rich_text = {
        "format": "rich_text_v1",
        "nodes": [{"type": "paragraph", "runs": [{"text": "x", "marks": []}]}],
    }
    blocks = _block_adapter.validate_python(
        [{"id": "c1", "type": "callout", "tone": "info", "text": rich_text}]
    )
    assert blocks[0].text.nodes[0].runs[0].text == "x"


def test_news_list_block_schema_is_registered() -> None:
    """Regression test: `news_list` (Task 040) was added to the domain validator but not to this
    Pydantic discriminated union, so the admin draft-save endpoint rejected it with a 422 for
    every bot that tried to embed a news feed on a category page."""
    blocks = _block_adapter.validate_python(
        [{"id": "n1", "type": "news_list", "title": "Новости"}]
    )
    assert blocks[0].type == "news_list"


def test_content_block_union_rejects_unknown_type() -> None:
    with pytest.raises(Exception):
        _block_adapter.validate_python([{"id": "x1", "type": "not_a_real_block"}])


def test_test_action_block_schema_is_registered() -> None:
    """Regression test: Task 068 added `test_action`/`test_catalog`/`test_attempt_history` to the
    domain validator (`content/domain/blocks.py`) and to `extract_test_references`/
    `remap_test_references`, but never to this Pydantic discriminated union -- so the admin
    draft-save/publish endpoints rejected every one of these blocks with a 422 before the request
    ever reached the domain layer that already knew how to validate it (Task 070)."""
    blocks = _block_adapter.validate_python(
        [{"id": "t1", "type": "test_action", "test_id": 9, "title": "Пройти тест"}]
    )
    assert blocks[0].type == "test_action"
    assert blocks[0].test_id == 9


def test_test_catalog_block_schema_is_registered() -> None:
    blocks = _block_adapter.validate_python(
        [{"id": "t2", "type": "test_catalog", "title": "Доступные тесты"}]
    )
    assert blocks[0].type == "test_catalog"


def test_test_attempt_history_block_schema_is_registered() -> None:
    blocks = _block_adapter.validate_python(
        [{"id": "t3", "type": "test_attempt_history", "title": "Мои результаты"}]
    )
    assert blocks[0].type == "test_attempt_history"
