from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import BlockValidationError
from .primitives import items, list_of_lists, strict_keys, text, url

# A `paragraph`/`callout` block's `text` field accepts either shape forever:
#   - a legacy plain string (unformatted, exactly today's behavior) -- an immutable published
#     content version may hold this shape and must keep rendering unchanged;
#   - this typed rich-text document -- the only shape the admin's WYSIWYG editor writes.
# There is no third, arbitrary-HTML/editor-native-JSON shape: this fixed, fully-specified grammar
# is what keeps rich text a typed contract instead of a generic JSON escape hatch.
RICH_TEXT_FORMAT = "rich_text_v1"
MARKS = ("bold", "italic", "underline", "strike")
MAX_RUN_TEXT = 2000
MAX_RUNS_PER_LINE = 200
MAX_LIST_ITEMS = 100
MAX_NODES = 300


def _validate_run(value: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BlockValidationError("Run must be an object", path=path)
    strict_keys(value, required={"text"}, optional={"marks", "href"}, path=path)
    run_text = text(value["text"], path=f"{path}.text", maximum=MAX_RUN_TEXT)
    marks_value = value.get("marks", [])
    if not isinstance(marks_value, list) or not all(isinstance(m, str) for m in marks_value):
        raise BlockValidationError("marks must be a list of strings", path=f"{path}.marks")
    unknown_marks = set(marks_value) - set(MARKS)
    if unknown_marks:
        raise BlockValidationError(
            f"Unknown marks: {', '.join(sorted(unknown_marks))}", path=f"{path}.marks"
        )
    marks = [mark for mark in MARKS if mark in marks_value]
    href = url(value.get("href"), path=f"{path}.href", required=False)
    return {"text": run_text, "marks": marks, "href": href}


def _validate_runs(value: Any, *, path: str, maximum: int = MAX_RUNS_PER_LINE) -> list[dict[str, Any]]:
    return [
        _validate_run(run, path=f"{path}[{index}]")
        for index, run in enumerate(items(value, path=path, maximum=maximum))
    ]


def validate_rich_text(value: Any, *, path: str, maximum_nodes: int = MAX_NODES) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BlockValidationError("Rich text must be an object", path=path)
    strict_keys(value, required={"format", "nodes"}, path=path)
    if value["format"] != RICH_TEXT_FORMAT:
        raise BlockValidationError("Unsupported rich text format", path=f"{path}.format")
    nodes_value = items(value["nodes"], path=f"{path}.nodes", maximum=maximum_nodes)
    nodes: list[dict[str, Any]] = []
    for index, node in enumerate(nodes_value):
        node_path = f"{path}.nodes[{index}]"
        node_type = node.get("type")
        if node_type == "paragraph":
            strict_keys(node, required={"type", "runs"}, path=node_path)
            nodes.append(
                {"type": "paragraph", "runs": _validate_runs(node["runs"], path=f"{node_path}.runs")}
            )
        elif node_type in {"bullet_list", "ordered_list"}:
            strict_keys(node, required={"type", "items"}, path=node_path)
            raw_items = list_of_lists(node["items"], path=f"{node_path}.items", maximum=MAX_LIST_ITEMS)
            list_items = [
                _validate_runs(item_runs, path=f"{node_path}.items[{item_index}]")
                for item_index, item_runs in enumerate(raw_items)
            ]
            nodes.append({"type": node_type, "items": list_items})
        else:
            raise BlockValidationError(
                f"Unknown rich text node type: {node_type!r}", path=f"{node_path}.type"
            )
    if not nodes:
        raise BlockValidationError("Rich text cannot be empty", path=f"{path}.nodes")
    return {"format": RICH_TEXT_FORMAT, "nodes": nodes}


def validate_formatted_text(
    value: Any, *, path: str, maximum: int, required: bool = True
) -> str | dict[str, Any] | None:
    if value is None and not required:
        return None
    if isinstance(value, str):
        return text(value, path=path, maximum=maximum, required=required)
    if isinstance(value, Mapping):
        return validate_rich_text(value, path=path)
    raise BlockValidationError("Expected text or rich text", path=path)
