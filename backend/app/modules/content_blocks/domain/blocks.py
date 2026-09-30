from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .errors import BlockValidationError
from .primitives import items, strict_keys, text, url
from .rich_text import validate_formatted_text

# The content-shaping block types shared between `content` category pages and `news` item
# bodies. Navigational/system block types (category_grid, tabs, form_catalog,
# submission_history, faq_list, news_list, capability_action, form_action) only make sense on a
# full category page and stay owned by the `content` module alone.
SHARED_BLOCK_TYPES = frozenset({"heading", "paragraph", "callout", "contact_list", "link", "file_list"})


def _base(block_id: str, block_type: str) -> dict[str, Any]:
    return {"id": block_id, "type": block_type}


def validate_heading(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "text", "level"}, path=path)
    if block["level"] not in (1, 2, 3, 4, 5, 6):
        raise BlockValidationError("Heading level must be 1, 2, 3, 4, 5, 6", path=f"{path}.level")
    return {
        **_base(block_id, "heading"),
        "text": text(block["text"], path=f"{path}.text", maximum=300),
        "level": block["level"],
    }


def validate_paragraph(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "text"}, path=path)
    return {
        **_base(block_id, "paragraph"),
        "text": validate_formatted_text(block["text"], path=f"{path}.text", maximum=10000),
    }


def validate_callout(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "text", "tone"}, optional={"title"}, path=path)
    if block["tone"] not in {"info", "warning", "success", "danger"}:
        raise BlockValidationError("Invalid callout tone", path=f"{path}.tone")
    return {
        **_base(block_id, "callout"),
        "title": text(block.get("title"), path=f"{path}.title", maximum=300, required=False),
        "text": validate_formatted_text(block["text"], path=f"{path}.text", maximum=5000),
        "tone": block["tone"],
    }


def validate_contact_list(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "items"}, path=path)
    contacts: list[dict[str, Any]] = []
    for index, item in enumerate(items(block["items"], path=f"{path}.items", maximum=30)):
        item_path = f"{path}.items[{index}]"
        strict_keys(item, required={"label", "value"}, optional={"href"}, path=item_path)
        contacts.append(
            {
                "label": text(item["label"], path=f"{item_path}.label", maximum=200),
                "value": text(item["value"], path=f"{item_path}.value", maximum=500),
                "href": url(item.get("href"), path=f"{item_path}.href", required=False),
            }
        )
    return {**_base(block_id, "contact_list"), "items": contacts}


def validate_link(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "title", "href", "style", "external"}, path=path)
    if block["style"] not in {"card", "button"}:
        raise BlockValidationError("Invalid link style", path=f"{path}.style")
    if not isinstance(block["external"], bool):
        raise BlockValidationError("external must be boolean", path=f"{path}.external")
    return {
        **_base(block_id, "link"),
        "title": text(block["title"], path=f"{path}.title", maximum=300),
        "href": url(block["href"], path=f"{path}.href"),
        "style": block["style"],
        "external": block["external"],
    }


def validate_file_list(block: Mapping[str, Any], *, block_id: str, path: str) -> dict[str, Any]:
    strict_keys(block, required={"id", "type", "items"}, path=path)
    files: list[dict[str, Any]] = []
    for index, item in enumerate(items(block["items"], path=f"{path}.items", maximum=30)):
        item_path = f"{path}.items[{index}]"
        strict_keys(
            item,
            required={"attachment_id", "title"},
            optional={"description", "display_mode"},
            path=item_path,
        )
        attachment_id = item["attachment_id"]
        if not isinstance(attachment_id, int) or attachment_id <= 0:
            raise BlockValidationError("Invalid attachment id", path=f"{item_path}.attachment_id")
        display_mode = item.get("display_mode", "tile")
        if display_mode not in {"tile", "inline_image"}:
            raise BlockValidationError("Invalid display mode", path=f"{item_path}.display_mode")
        files.append(
            {
                "attachment_id": attachment_id,
                "title": text(item["title"], path=f"{item_path}.title", maximum=300),
                "description": text(
                    item.get("description"),
                    path=f"{item_path}.description",
                    maximum=1000,
                    required=False,
                ),
                "display_mode": display_mode,
            }
        )
    return {**_base(block_id, "file_list"), "items": files}


_VALIDATORS = {
    "heading": validate_heading,
    "paragraph": validate_paragraph,
    "callout": validate_callout,
    "contact_list": validate_contact_list,
    "link": validate_link,
    "file_list": validate_file_list,
}


def validate_shared_block(
    block_type: Any, block: Mapping[str, Any], *, block_id: str, path: str
) -> dict[str, Any] | None:
    """Returns the validated block, or None if `block_type` is not one of the shared kernel's
    content-shaping types -- callers fall through to their own module-specific block types."""
    validator = _VALIDATORS.get(block_type)
    if validator is None:
        return None
    return validator(block, block_id=block_id, path=path)


def extract_file_list_attachment_ids(blocks: Iterable[Mapping[str, Any]]) -> set[int]:
    attachment_ids: set[int] = set()
    for block in blocks:
        if block.get("type") == "file_list":
            attachment_ids.update(int(item["attachment_id"]) for item in block["items"])
    return attachment_ids
