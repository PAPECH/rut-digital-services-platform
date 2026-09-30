from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from ...content_blocks.domain.blocks import extract_file_list_attachment_ids, validate_shared_block
from ...content_blocks.domain.errors import BlockValidationError
from ...content_blocks.domain.primitives import items as _items
from ...content_blocks.domain.primitives import stable_id as _stable_id
from ...content_blocks.domain.primitives import strict_keys as _strict_keys
from ...content_blocks.domain.primitives import text as _text

TAB_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_ROOT_BLOCKS = 80
MAX_NESTED_BLOCKS = 30


def _validate_titled_items(value: Any, *, path: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    item_ids: set[str] = set()
    for index, item in enumerate(_items(value, path=path)):
        item_path = f"{path}[{index}]"
        _strict_keys(item, required={"id", "title", "text"}, path=item_path)
        item_id = _stable_id(item["id"], path=f"{item_path}.id")
        if item_id in item_ids:
            raise BlockValidationError("Duplicate item id", path=f"{item_path}.id")
        item_ids.add(item_id)
        result.append(
            {
                "id": item_id,
                "title": _text(item["title"], path=f"{item_path}.title", maximum=300),
                "text": _text(item["text"], path=f"{item_path}.text", maximum=5000),
            }
        )
    return result


def validate_blocks(
    blocks: Iterable[Mapping[str, Any]],
    *,
    allow_tabs: bool = True,
    path: str = "blocks",
    seen_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(blocks, list):
        raise BlockValidationError("Blocks must be a list", path=path)
    maximum = MAX_ROOT_BLOCKS if allow_tabs else MAX_NESTED_BLOCKS
    if len(blocks) > maximum:
        raise BlockValidationError(f"Too many blocks; maximum is {maximum}", path=path)
    global_ids = seen_ids if seen_ids is not None else set()
    validated = [
        _validate_block(block, path=f"{path}[{index}]", allow_tabs=allow_tabs, seen_ids=global_ids)
        for index, block in enumerate(blocks)
    ]
    if allow_tabs:
        for interactive_type in (
            "form_catalog",
            "submission_history",
            "faq_list",
            "news_list",
            "test_catalog",
            "test_attempt_history",
        ):
            if sum(block["type"] == interactive_type for block in validated) > 1:
                raise BlockValidationError(
                    f"Only one {interactive_type} block is allowed per page",
                    path=path,
                )
    return validated


def _validate_block(
    block: Mapping[str, Any],
    *,
    path: str,
    allow_tabs: bool,
    seen_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(block, Mapping):
        raise BlockValidationError("Block must be an object", path=path)
    block_id = _stable_id(block.get("id"), path=f"{path}.id")
    if block_id in seen_ids:
        raise BlockValidationError("Duplicate block id", path=f"{path}.id")
    seen_ids.add(block_id)
    block_type = block.get("type")
    base = {"id": block_id, "type": block_type}

    shared_result = validate_shared_block(block_type, block, block_id=block_id, path=path)
    if shared_result is not None:
        return shared_result

    if block_type in {"accordion", "steps"}:
        _strict_keys(block, required={"id", "type", "items"}, path=path)
        return {**base, "items": _validate_titled_items(block["items"], path=f"{path}.items")}

    if block_type == "form_action":
        _strict_keys(
            block,
            required={"id", "type", "form_id"},
            optional={"description", 'title'},
            path=path,
        )
        if not isinstance(block["form_id"], int) or block["form_id"] <= 0:
            raise BlockValidationError("Invalid form id", path=f"{path}.form_id")
        return {
            **base,
            "form_id": block["form_id"],
            "title": _text(block["title"], path=f"{path}.title", maximum=300, required=False),
            "description": _text(
                block.get("description"),
                path=f"{path}.description",
                maximum=1000,
                required=False,
            ),
        }

    if block_type == "capability_action":
        _strict_keys(
            block,
            required={"id", "type", "capability_key", "view_key", "title"},
            optional={"description"},
            path=path,
        )
        capability_key = block["capability_key"]
        view_key = block["view_key"]
        if not isinstance(capability_key, str) or not re.fullmatch(r"^[a-z][a-z0-9_]{1,63}$", capability_key):
            raise BlockValidationError("Invalid capability key", path=f"{path}.capability_key")
        if not isinstance(view_key, str) or not re.fullmatch(r"^[a-z][a-z0-9_-]{1,63}$", view_key):
            raise BlockValidationError("Invalid capability view key", path=f"{path}.view_key")
        return {
            **base,
            "capability_key": capability_key,
            "view_key": view_key,
            "title": _text(block["title"], path=f"{path}.title", maximum=300),
            "description": _text(
                block.get("description"),
                path=f"{path}.description",
                maximum=1000,
                required=False,
            ),
        }

    if block_type == "category_grid":
        if not allow_tabs:
            raise BlockValidationError(
                "Interactive system blocks are only allowed at page root",
                path=path,
            )
        _strict_keys(
            block,
            required={"id", "type"},
            optional={"parent_id", "title"},
            path=path,
        )
        parent_id = block.get("parent_id")
        if parent_id is not None and (
            not isinstance(parent_id, int) or isinstance(parent_id, bool) or parent_id <= 0
        ):
            raise BlockValidationError("Invalid parent category id", path=f"{path}.parent_id")
        return {
            **base,
            "parent_id": parent_id,
            "title": _text(
                block.get("title"),
                path=f"{path}.title",
                maximum=300,
                required=False,
            ),
        }

    if block_type == "test_action":
        _strict_keys(
            block,
            required={"id", "type", "test_id"},
            optional={"description", "title"},
            path=path,
        )
        if not isinstance(block["test_id"], int) or isinstance(block["test_id"], bool) or block["test_id"] <= 0:
            raise BlockValidationError("Invalid test id", path=f"{path}.test_id")
        return {
            **base,
            "test_id": block["test_id"],
            "title": _text(block.get("title"), path=f"{path}.title", maximum=300, required=False),
            "description": _text(
                block.get("description"),
                path=f"{path}.description",
                maximum=1000,
                required=False,
            ),
        }

    if block_type in {
        "form_catalog",
        "submission_history",
        "faq_list",
        "news_list",
        "test_catalog",
        "test_attempt_history",
    }:
        if not allow_tabs:
            raise BlockValidationError(
                "Interactive system blocks are only allowed at page root",
                path=path,
            )
        _strict_keys(
            block,
            required={"id", "type"},
            optional={"title"},
            path=path,
        )
        return {
            **base,
            "title": _text(
                block.get("title"),
                path=f"{path}.title",
                maximum=300,
                required=False,
            ),
        }

    if block_type == "tabs":
        if not allow_tabs:
            raise BlockValidationError("Nested tabs are not allowed", path=path)
        _strict_keys(block, required={"id", "type", "tabs"}, path=path)
        tabs: list[dict[str, Any]] = []
        tab_keys: set[str] = set()
        for index, tab in enumerate(_items(block["tabs"], path=f"{path}.tabs", maximum=12)):
            tab_path = f"{path}.tabs[{index}]"
            _strict_keys(tab, required={"key", "title", "blocks"}, path=tab_path)
            key = tab["key"]
            if not isinstance(key, str) or not TAB_KEY_RE.fullmatch(key):
                raise BlockValidationError("Invalid tab key", path=f"{tab_path}.key")
            if key in tab_keys:
                raise BlockValidationError("Duplicate tab key", path=f"{tab_path}.key")
            tab_keys.add(key)
            tabs.append(
                {
                    "key": key,
                    "title": _text(tab["title"], path=f"{tab_path}.title", maximum=200),
                    "blocks": validate_blocks(
                        tab["blocks"],
                        allow_tabs=False,
                        path=f"{tab_path}.blocks",
                        seen_ids=seen_ids,
                    ),
                }
            )
        return {**base, "tabs": tabs}

    raise BlockValidationError(f"Unknown block type: {block_type!r}", path=f"{path}.type")


def extract_references(blocks: Iterable[Mapping[str, Any]]) -> tuple[set[int], set[int]]:
    form_ids: set[int] = set()
    attachment_ids: set[int] = set()
    for block in blocks:
        if block.get("type") == "form_action":
            form_ids.add(int(block["form_id"]))
        elif block.get("type") == "file_list":
            attachment_ids.update(extract_file_list_attachment_ids([block]))
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                nested_forms, nested_attachments = extract_references(tab["blocks"])
                form_ids.update(nested_forms)
                attachment_ids.update(nested_attachments)
    return form_ids, attachment_ids


def extract_inline_image_attachment_ids(blocks: Iterable[Mapping[str, Any]]) -> set[int]:
    """`file_list` items with `display_mode == 'inline_image'` -- these must resolve to an
    `image/*` attachment, checked against real mime data by the application layer (the domain
    layer only knows the shape, not what any given attachment's mime actually is)."""
    attachment_ids: set[int] = set()
    for block in blocks:
        if block.get("type") == "file_list":
            attachment_ids.update(
                int(item["attachment_id"])
                for item in block["items"]
                if item.get("display_mode") == "inline_image"
            )
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                attachment_ids.update(extract_inline_image_attachment_ids(tab["blocks"]))
    return attachment_ids


_IMAGE_URL_ATTACHMENT_ID_RE = re.compile(r"/api/files/(\d+)(?:[/?]|$)")


def extract_card_image_attachment_id(image_url: str | None) -> int | None:
    """`image_url` is a stored signed URL string (`/api/files/{id}?exp=...&sig=...`), not a bare
    attachment id -- best-effort parse for reference tracking. Returns None for anything that
    doesn't match that shape (e.g. an externally hosted image predating this table) rather than
    raising, since a card image that isn't one of this bot's own attachments simply has no
    `card_image` reference to record."""
    if not image_url:
        return None
    match = _IMAGE_URL_ATTACHMENT_ID_RE.search(image_url)
    return int(match.group(1)) if match else None


def extract_capability_references(
    blocks: Iterable[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    references: set[tuple[str, str]] = set()
    for block in blocks:
        if block.get("type") == "capability_action":
            references.add((str(block["capability_key"]), str(block["view_key"])))
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                references.update(extract_capability_references(tab["blocks"]))
    return references


def extract_category_references(blocks: Iterable[Mapping[str, Any]]) -> set[int]:
    """`category_grid.parent_id` values that must resolve to a tenant-owned category."""
    references: set[int] = set()
    for block in blocks:
        if block.get("type") == "category_grid" and block.get("parent_id") is not None:
            references.add(int(block["parent_id"]))
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                references.update(extract_category_references(tab["blocks"]))
    return references


def extract_test_references(blocks: Iterable[Mapping[str, Any]]) -> set[int]:
    """`test_action.test_id` values that must resolve to a tenant-owned `form_tests` row
    (Task 068) -- a separate function rather than folding into `extract_references`'s
    `(form_ids, attachment_ids)` tuple, mirroring `extract_capability_references`/
    `extract_category_references`'s own precedent of one function per reference kind."""
    references: set[int] = set()
    for block in blocks:
        if block.get("type") == "test_action":
            references.add(int(block["test_id"]))
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                references.update(extract_test_references(tab["blocks"]))
    return references


def clone_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(blocks)


def remap_form_references(
    blocks: list[dict[str, Any]],
    form_id_mapping: Mapping[int, int],
) -> list[dict[str, Any]]:
    """Clone content blocks and replace tenant-local form IDs."""

    remapped = clone_blocks(blocks)
    for block in remapped:
        if block.get("type") == "form_action":
            source_id = int(block["form_id"])
            block["form_id"] = form_id_mapping[source_id]
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                tab["blocks"] = remap_form_references(tab["blocks"], form_id_mapping)
    return remapped


def remap_test_references(
    blocks: list[dict[str, Any]],
    test_id_mapping: Mapping[int, int],
) -> list[dict[str, Any]]:
    """Clone content blocks and replace tenant-local test IDs -- the `test_action` counterpart
    to `remap_form_references`, needed so a content clone across bots (Task 033) doesn't leave
    a `test_action` block pointing at a `test_id` that only resolves in the source bot."""

    remapped = clone_blocks(blocks)
    for block in remapped:
        if block.get("type") == "test_action":
            source_id = int(block["test_id"])
            block["test_id"] = test_id_mapping[source_id]
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                tab["blocks"] = remap_test_references(tab["blocks"], test_id_mapping)
    return remapped


def remap_attachment_and_category_references(
    blocks: list[dict[str, Any]],
    attachment_id_mapping: Mapping[int, int],
    category_id_mapping: Mapping[int, int],
) -> list[dict[str, Any]]:
    """Clone content blocks and replace tenant-local attachment and category IDs -- the
    counterpart to `remap_form_references` for content import/clone flows (Task 033)."""

    remapped = clone_blocks(blocks)
    for block in remapped:
        if block.get("type") == "file_list":
            for item in block["items"]:
                source_id = int(item["attachment_id"])
                item["attachment_id"] = attachment_id_mapping[source_id]
        elif block.get("type") == "category_grid":
            parent_id = block.get("parent_id")
            if parent_id is not None:
                block["parent_id"] = category_id_mapping[int(parent_id)]
        elif block.get("type") == "tabs":
            for tab in block["tabs"]:
                tab["blocks"] = remap_attachment_and_category_references(
                    tab["blocks"], attachment_id_mapping, category_id_mapping
                )
    return remapped
