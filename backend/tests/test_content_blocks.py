from __future__ import annotations

import pytest

from app.modules.content.domain.blocks import (
    BlockValidationError,
    extract_card_image_attachment_id,
    extract_inline_image_attachment_ids,
    extract_test_references,
    remap_attachment_and_category_references,
    remap_test_references,
    validate_blocks,
)


def test_news_list_block_is_valid_at_root() -> None:
    blocks = validate_blocks([{"id": "news", "type": "news_list", "title": "Новости"}])
    assert blocks == [{"id": "news", "type": "news_list", "title": "Новости"}]


def test_news_list_block_rejects_second_instance_per_page() -> None:
    blocks = [
        {"id": "news1", "type": "news_list"},
        {"id": "news2", "type": "news_list"},
    ]
    with pytest.raises(BlockValidationError):
        validate_blocks(blocks)


def test_news_list_block_rejects_nesting_in_tabs() -> None:
    blocks = [
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {"key": "a", "title": "A", "blocks": [{"id": "news", "type": "news_list"}]}
            ],
        }
    ]
    with pytest.raises(BlockValidationError):
        validate_blocks(blocks)


def test_paragraph_still_accepts_legacy_plain_string_text() -> None:
    blocks = validate_blocks([{"id": "p1", "type": "paragraph", "text": "Обычный текст"}])
    assert blocks[0]["text"] == "Обычный текст"


def test_paragraph_accepts_rich_text_with_marks_and_list() -> None:
    rich_text = {
        "format": "rich_text_v1",
        "nodes": [
            {
                "type": "paragraph",
                "runs": [
                    {"text": "Привет, ", "marks": []},
                    {"text": "мир", "marks": ["bold", "italic"]},
                ],
            },
            {
                "type": "bullet_list",
                "items": [
                    [{"text": "Пункт один", "marks": []}],
                    [{"text": "Пункт два", "marks": ["underline"]}],
                ],
            },
        ],
    }
    blocks = validate_blocks([{"id": "p1", "type": "paragraph", "text": rich_text}])
    assert blocks[0]["text"]["nodes"][0]["runs"][1]["marks"] == ["bold", "italic"]
    assert blocks[0]["text"]["nodes"][1]["items"][1][0]["marks"] == ["underline"]


def test_callout_rich_text_rejects_unknown_mark() -> None:
    rich_text = {
        "format": "rich_text_v1",
        "nodes": [{"type": "paragraph", "runs": [{"text": "x", "marks": ["blink"]}]}],
    }
    with pytest.raises(BlockValidationError):
        validate_blocks(
            [{"id": "c1", "type": "callout", "tone": "info", "text": rich_text}]
        )


def test_rich_text_link_run_requires_valid_href() -> None:
    rich_text = {
        "format": "rich_text_v1",
        "nodes": [
            {"type": "paragraph", "runs": [{"text": "link", "marks": [], "href": "javascript:alert(1)"}]}
        ],
    }
    with pytest.raises(BlockValidationError):
        validate_blocks([{"id": "p1", "type": "paragraph", "text": rich_text}])


def test_rich_text_cannot_be_empty() -> None:
    rich_text = {"format": "rich_text_v1", "nodes": []}
    with pytest.raises(BlockValidationError):
        validate_blocks([{"id": "p1", "type": "paragraph", "text": rich_text}])


@pytest.mark.parametrize(
    "block",
    [
        {"id": "heading", "type": "heading", "text": "Заголовок", "level": 2},
        {"id": "paragraph", "type": "paragraph", "text": "Строка 1\nСтрока 2"},
        {
            "id": "callout",
            "type": "callout",
            "title": "Важно",
            "text": "Сообщение",
            "tone": "warning",
        },
        {
            "id": "contacts",
            "type": "contact_list",
            "items": [{"label": "Телефон", "value": "+7", "href": "tel:+70000000000"}],
        },
        {
            "id": "accordion",
            "type": "accordion",
            "items": [{"id": "answer", "title": "Вопрос", "text": "Ответ"}],
        },
        {
            "id": "steps",
            "type": "steps",
            "items": [{"id": "step", "title": "Шаг", "text": "Описание"}],
        },
        {
            "id": "link",
            "type": "link",
            "title": "Сайт",
            "href": "https://example.com",
            "style": "button",
            "external": True,
        },
        {
            "id": "files",
            "type": "file_list",
            "items": [{"attachment_id": 1, "title": "Заявление"}],
        },
        {
            "id": "form",
            "type": "form_action",
            "form_id": 4,
            "title": "Заполнить форму",
        },
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "staff",
                    "title": "Сотрудникам",
                    "blocks": [{"id": "tab_text", "type": "paragraph", "text": "Содержимое"}],
                }
            ],
        },
        {"id": "forms", "type": "form_catalog", "title": "Доступные формы"},
        {"id": "history", "type": "submission_history", "title": "Мои заявки"},
        {"id": "faq", "type": "faq_list", "title": "Частые вопросы"},
        {
            "id": "test",
            "type": "test_action",
            "test_id": 4,
            "title": "Пройти тест",
        },
        {"id": "tests", "type": "test_catalog", "title": "Доступные тесты"},
        {"id": "test_history", "type": "test_attempt_history", "title": "Мои результаты"},
        {"id": "grid_root", "type": "category_grid"},
        {"id": "grid_scoped", "type": "category_grid", "parent_id": 5, "title": "Подкатегории"},
    ],
)
def test_each_supported_block_type_is_accepted(block: dict) -> None:
    assert validate_blocks([block])[0]["type"] == block["type"]


@pytest.mark.parametrize(
    "block",
    [
        {"id": "unknown", "type": "html", "html": "<script>alert(1)</script>"},
        {
            "id": "link",
            "type": "link",
            "title": "Опасная ссылка",
            "href": "javascript:alert(1)",
            "style": "button",
            "external": True,
        },
        {
            "id": "paragraph",
            "type": "paragraph",
            "text": "Текст",
            "html": "<b>Текст</b>",
        },
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "nested",
                    "title": "Вложенная",
                    "blocks": [
                        {
                            "id": "nested_tabs",
                            "type": "tabs",
                            "tabs": [{"key": "inner", "title": "Внутри", "blocks": []}],
                        }
                    ],
                }
            ],
        },
    ],
)
def test_unsafe_or_unknown_block_payload_is_rejected(block: dict) -> None:
    with pytest.raises(BlockValidationError):
        validate_blocks([block])


@pytest.mark.parametrize(
    "block_type",
    ["form_catalog", "submission_history", "faq_list", "category_grid", "test_catalog", "test_attempt_history"],
)
def test_interactive_system_blocks_are_rejected_inside_tabs(block_type: str) -> None:
    with pytest.raises(BlockValidationError, match="only allowed at page root"):
        validate_blocks(
            [
                {
                    "id": "tabs",
                    "type": "tabs",
                    "tabs": [
                        {
                            "key": "system",
                            "title": "Системный блок",
                            "blocks": [
                                {"id": "interactive", "type": block_type, "title": None}
                            ],
                        }
                    ],
                }
            ]
        )


def test_category_grid_allows_repeats_with_different_parents() -> None:
    """Unlike form_catalog/submission_history/faq_list, more than one category_grid block is
    allowed -- each can point at a different parent_id and is a legitimately different view."""
    validated = validate_blocks(
        [
            {"id": "top_level", "type": "category_grid"},
            {"id": "scoped", "type": "category_grid", "parent_id": 3},
        ]
    )
    assert [block["type"] for block in validated] == ["category_grid", "category_grid"]


def test_category_grid_rejects_invalid_parent_id() -> None:
    with pytest.raises(BlockValidationError, match="Invalid parent category id"):
        validate_blocks([{"id": "grid", "type": "category_grid", "parent_id": -1}])
    with pytest.raises(BlockValidationError, match="Invalid parent category id"):
        validate_blocks([{"id": "grid", "type": "category_grid", "parent_id": "3"}])


@pytest.mark.parametrize(
    "block_type", ["form_catalog", "submission_history", "faq_list", "test_catalog", "test_attempt_history"]
)
def test_interactive_system_blocks_cannot_be_duplicated(block_type: str) -> None:
    with pytest.raises(BlockValidationError, match="Only one"):
        validate_blocks(
            [
                {"id": "first", "type": block_type, "title": None},
                {"id": "second", "type": block_type, "title": None},
            ]
        )


def test_duplicate_ids_and_tab_keys_are_rejected() -> None:
    duplicate_blocks = [
        {"id": "same", "type": "paragraph", "text": "Первый"},
        {"id": "same", "type": "paragraph", "text": "Второй"},
    ]
    duplicate_tabs = [
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {"key": "same", "title": "Первый", "blocks": []},
                {"key": "same", "title": "Второй", "blocks": []},
            ],
        }
    ]

    with pytest.raises(BlockValidationError, match="Duplicate block id"):
        validate_blocks(duplicate_blocks)
    with pytest.raises(BlockValidationError, match="Duplicate tab key"):
        validate_blocks(duplicate_tabs)


def test_file_list_display_mode_defaults_to_tile_and_accepts_inline_image() -> None:
    default = validate_blocks(
        [{"id": "files", "type": "file_list", "items": [{"attachment_id": 1, "title": "Файл"}]}]
    )
    assert default[0]["items"][0]["display_mode"] == "tile"

    explicit = validate_blocks(
        [
            {
                "id": "files",
                "type": "file_list",
                "items": [
                    {"attachment_id": 1, "title": "Фото", "display_mode": "inline_image"}
                ],
            }
        ]
    )
    assert explicit[0]["items"][0]["display_mode"] == "inline_image"


def test_file_list_rejects_invalid_display_mode() -> None:
    with pytest.raises(BlockValidationError, match="Invalid display mode"):
        validate_blocks(
            [
                {
                    "id": "files",
                    "type": "file_list",
                    "items": [
                        {"attachment_id": 1, "title": "Файл", "display_mode": "carousel"}
                    ],
                }
            ]
        )


def test_extract_inline_image_attachment_ids_finds_only_inline_items_including_in_tabs() -> None:
    blocks = [
        {
            "id": "files",
            "type": "file_list",
            "items": [
                {"attachment_id": 1, "title": "Тайл", "display_mode": "tile"},
                {"attachment_id": 2, "title": "Картинка", "display_mode": "inline_image"},
            ],
        },
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "nested",
                    "title": "Вложенная",
                    "blocks": [
                        {
                            "id": "nested_files",
                            "type": "file_list",
                            "items": [
                                {"attachment_id": 3, "title": "Вложенная картинка", "display_mode": "inline_image"}
                            ],
                        }
                    ],
                }
            ],
        },
    ]
    assert extract_inline_image_attachment_ids(blocks) == {2, 3}


@pytest.mark.parametrize(
    ("image_url", "expected"),
    [
        ("/api/files/42?exp=123&sig=abc", 42),
        ("/api/files/7", 7),
        ("https://cdn.example.com/legacy/hero.png", None),
        (None, None),
        ("", None),
    ],
)
def test_extract_card_image_attachment_id_is_best_effort(image_url: str | None, expected: int | None) -> None:
    assert extract_card_image_attachment_id(image_url) == expected


def test_block_count_and_text_size_limits_are_enforced() -> None:
    too_many = [{"id": f"block_{index}", "type": "paragraph", "text": "Текст"} for index in range(81)]

    with pytest.raises(BlockValidationError, match="Too many blocks"):
        validate_blocks(too_many)
    with pytest.raises(BlockValidationError, match="exceeds 10000"):
        validate_blocks([{"id": "long", "type": "paragraph", "text": "x" * 10_001}])


def test_remap_attachment_and_category_references_replaces_ids_and_clones() -> None:
    blocks = [
        {
            "id": "files",
            "type": "file_list",
            "items": [
                {"attachment_id": 1, "title": "A"},
                {"attachment_id": 2, "title": "B"},
            ],
        },
        {"id": "grid", "type": "category_grid", "parent_id": 5},
        {"id": "unrelated", "type": "paragraph", "text": "unchanged"},
    ]

    remapped = remap_attachment_and_category_references(blocks, {1: 101, 2: 102}, {5: 205})

    assert remapped[0]["items"][0]["attachment_id"] == 101
    assert remapped[0]["items"][1]["attachment_id"] == 102
    assert remapped[1]["parent_id"] == 205
    assert remapped[2] == {"id": "unrelated", "type": "paragraph", "text": "unchanged"}
    # Source untouched -- this is a clone, not an in-place mutation.
    assert blocks[0]["items"][0]["attachment_id"] == 1


def test_remap_attachment_and_category_references_leaves_root_category_grid_untouched() -> None:
    blocks = [{"id": "grid", "type": "category_grid"}]

    remapped = remap_attachment_and_category_references(blocks, {}, {})

    assert remapped[0].get("parent_id") is None


def test_remap_attachment_and_category_references_raises_for_unmapped_id() -> None:
    blocks = [{"id": "files", "type": "file_list", "items": [{"attachment_id": 1, "title": "A"}]}]

    with pytest.raises(KeyError):
        remap_attachment_and_category_references(blocks, {}, {})


def test_remap_attachment_and_category_references_recurses_into_tabs() -> None:
    blocks = [
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "staff",
                    "title": "Сотрудникам",
                    "blocks": [
                        {
                            "id": "nested_files",
                            "type": "file_list",
                            "items": [{"attachment_id": 9, "title": "C"}],
                        },
                        {"id": "nested_grid", "type": "category_grid", "parent_id": 6},
                    ],
                }
            ],
        }
    ]

    remapped = remap_attachment_and_category_references(blocks, {9: 909}, {6: 606})

    nested = remapped[0]["tabs"][0]["blocks"]
    assert nested[0]["items"][0]["attachment_id"] == 909
    assert nested[1]["parent_id"] == 606


def test_test_action_rejects_invalid_test_id() -> None:
    with pytest.raises(BlockValidationError, match="Invalid test id"):
        validate_blocks([{"id": "test", "type": "test_action", "test_id": 0, "title": None}])
    with pytest.raises(BlockValidationError, match="Invalid test id"):
        validate_blocks([{"id": "test", "type": "test_action", "test_id": True, "title": None}])


def test_extract_test_references_finds_test_action_ids_including_in_tabs() -> None:
    blocks = [
        {"id": "t1", "type": "test_action", "test_id": 4, "title": None},
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "staff",
                    "title": "Сотрудникам",
                    "blocks": [{"id": "t2", "type": "test_action", "test_id": 7, "title": None}],
                }
            ],
        },
        {"id": "unrelated", "type": "paragraph", "text": "unchanged"},
    ]
    assert extract_test_references(blocks) == {4, 7}


def test_remap_test_references_replaces_ids_and_clones() -> None:
    blocks = [
        {"id": "test", "type": "test_action", "test_id": 4, "title": None},
        {"id": "unrelated", "type": "paragraph", "text": "unchanged"},
    ]

    remapped = remap_test_references(blocks, {4: 404})

    assert remapped[0]["test_id"] == 404
    assert remapped[1] == {"id": "unrelated", "type": "paragraph", "text": "unchanged"}
    assert blocks[0]["test_id"] == 4  # source untouched


def test_remap_test_references_raises_for_unmapped_id() -> None:
    blocks = [{"id": "test", "type": "test_action", "test_id": 4, "title": None}]
    with pytest.raises(KeyError):
        remap_test_references(blocks, {})


def test_remap_test_references_recurses_into_tabs() -> None:
    blocks = [
        {
            "id": "tabs",
            "type": "tabs",
            "tabs": [
                {
                    "key": "staff",
                    "title": "Сотрудникам",
                    "blocks": [{"id": "t", "type": "test_action", "test_id": 9, "title": None}],
                }
            ],
        }
    ]
    remapped = remap_test_references(blocks, {9: 909})
    assert remapped[0]["tabs"][0]["blocks"][0]["test_id"] == 909
