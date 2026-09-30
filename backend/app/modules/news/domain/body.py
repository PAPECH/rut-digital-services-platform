from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ...content_blocks.domain.blocks import extract_file_list_attachment_ids, validate_shared_block
from ...content_blocks.domain.errors import BlockValidationError
from ...content_blocks.domain.primitives import stable_id

# A news item's body may only use the shared kernel's content-shaping block types (heading,
# paragraph, callout, contact_list, link, file_list) -- the navigational/system block types that
# make sense on a category page (category_grid, tabs, form_catalog, submission_history, faq_list,
# news_list, capability_action, form_action) are rejected the same way an unknown type is.
MAX_BODY_BLOCKS = 60


def validate_news_body(blocks: Any, *, path: str = "body_blocks") -> list[dict[str, Any]]:
    if not isinstance(blocks, list) or not blocks:
        raise BlockValidationError("News body cannot be empty", path=path)
    if len(blocks) > MAX_BODY_BLOCKS:
        raise BlockValidationError(f"Too many blocks; maximum is {MAX_BODY_BLOCKS}", path=path)
    seen_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        item_path = f"{path}[{index}]"
        if not isinstance(block, Mapping):
            raise BlockValidationError("Block must be an object", path=item_path)
        block_id = stable_id(block.get("id"), path=f"{item_path}.id")
        if block_id in seen_ids:
            raise BlockValidationError("Duplicate block id", path=f"{item_path}.id")
        seen_ids.add(block_id)
        block_type = block.get("type")
        result = validate_shared_block(block_type, block, block_id=block_id, path=item_path)
        if result is None:
            raise BlockValidationError(
                f"Block type not allowed in a news body: {block_type!r}", path=f"{item_path}.type"
            )
        validated.append(result)
    return validated


def extract_body_attachment_ids(blocks: Iterable[Mapping[str, Any]]) -> set[int]:
    return extract_file_list_attachment_ids(blocks)
