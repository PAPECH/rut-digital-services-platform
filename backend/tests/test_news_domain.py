from __future__ import annotations

import pytest

from app.modules.content_blocks.domain.errors import BlockValidationError
from app.modules.news.domain.body import validate_news_body
from app.modules.news.domain.entities import InvalidNewsItem, NewsItem

_PARAGRAPH = {"id": "p1", "type": "paragraph", "text": "Текст новости"}


def test_validate_news_body_accepts_shared_block_types() -> None:
    blocks = validate_news_body(
        [
            {"id": "h1", "type": "heading", "text": "Заголовок", "level": 2},
            _PARAGRAPH,
            {"id": "c1", "type": "callout", "tone": "warning", "text": "Важно"},
            {
                "id": "contacts",
                "type": "contact_list",
                "items": [{"label": "Тел.", "value": "+7"}],
            },
            {
                "id": "link1",
                "type": "link",
                "title": "Сайт",
                "href": "https://example.com",
                "style": "card",
                "external": True,
            },
            {
                "id": "files1",
                "type": "file_list",
                "items": [{"attachment_id": 1, "title": "Фото"}],
            },
        ]
    )
    assert [b["type"] for b in blocks] == [
        "heading",
        "paragraph",
        "callout",
        "contact_list",
        "link",
        "file_list",
    ]


@pytest.mark.parametrize(
    "block",
    [
        {"id": "grid", "type": "category_grid"},
        {"id": "tabs", "type": "tabs", "tabs": []},
        {"id": "form_catalog", "type": "form_catalog"},
        {"id": "submission_history", "type": "submission_history"},
        {"id": "faq_list", "type": "faq_list"},
        {"id": "news_list", "type": "news_list"},
        {"id": "form_action", "type": "form_action", "form_id": 1},
        {
            "id": "capability_action",
            "type": "capability_action",
            "capability_key": "request_status",
            "view_key": "lookup",
            "title": "Статус",
        },
    ],
)
def test_validate_news_body_rejects_navigational_system_blocks(block) -> None:
    with pytest.raises(BlockValidationError):
        validate_news_body([block])


def test_validate_news_body_rejects_empty_list() -> None:
    with pytest.raises(BlockValidationError):
        validate_news_body([])


def test_validate_news_body_rejects_duplicate_block_ids() -> None:
    with pytest.raises(BlockValidationError):
        validate_news_body([_PARAGRAPH, dict(_PARAGRAPH)])


def test_news_item_requires_non_empty_title() -> None:
    with pytest.raises(InvalidNewsItem):
        NewsItem(
            id=None,
            bot_instance_id=1,
            title="   ",
            body_blocks=[_PARAGRAPH],
        )


def test_news_item_normalizes_optional_fields_and_defaults_published_at() -> None:
    item = NewsItem(
        id=None,
        bot_instance_id=1,
        title="  Заголовок  ",
        body_blocks=[_PARAGRAPH],
        title_en="  Title  ",
        category="  Спорт  ",
    )
    assert item.title == "Заголовок"
    assert item.title_en == "Title"
    assert item.category == "Спорт"
    assert item.published_at is not None


def test_news_item_rejects_invalid_cover_attachment_id() -> None:
    with pytest.raises(InvalidNewsItem):
        NewsItem(
            id=None,
            bot_instance_id=1,
            title="Заголовок",
            body_blocks=[_PARAGRAPH],
            cover_attachment_id=0,
        )


def test_news_item_rejects_category_too_long() -> None:
    with pytest.raises(InvalidNewsItem):
        NewsItem(
            id=None,
            bot_instance_id=1,
            title="Заголовок",
            body_blocks=[_PARAGRAPH],
            category="x" * 200,
        )


def test_news_item_propagates_body_validation_error() -> None:
    with pytest.raises(BlockValidationError):
        NewsItem(
            id=None,
            bot_instance_id=1,
            title="Заголовок",
            body_blocks=[{"id": "grid", "type": "category_grid"}],
        )
