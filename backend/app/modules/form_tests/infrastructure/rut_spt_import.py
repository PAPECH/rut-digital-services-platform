from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..domain.elements import CHOICE_TYPES, STRUCTURAL_TYPES

_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_SEPARATOR_CELL_RE = re.compile(r"^-{2,}$")
# RUT's source table hand-types a running number into the front of every question's and every
# option's text (`"1) Ваша фамилия"`, `"1 — Нет, это не так"`) -- purely the item's position in
# its own list, already implicit from array order and never meant to be admin-authored content.
# Stripped on import so numbering becomes a pure client-rendering concern (never stored) and stays
# correct automatically when questions are reordered/inserted/deleted.
_LEADING_NUMBER_RE = re.compile(r"^\d{1,3}\s*[)\-–—]\s*")


def _strip_leading_number(text: str) -> str:
    return _LEADING_NUMBER_RE.sub("", text, count=1)


class RutSptImportError(ValueError):
    """The source table doesn't match the expected 5-column shape (see README_import_monitoring_MAX.md:
    ID | Тип элемента | Текст | Вариант ответа | Балл)."""


def _split_row(line: str) -> list[str] | None:
    match = _ROW_RE.match(line.strip())
    if not match:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def _parse_required(cell: str) -> bool:
    """Blank (RUT's source has no such column -- every anketa/instrument question in it is in
    fact required) or anything other than an explicit false-ish value defaults to `True`,
    matching `parse_rut_spt_table`'s previous hardcoded `required=True`."""
    return cell.strip().lower() not in {"false", "0", "нет", "no"}


def build_elements_from_rows(
    rows: Iterable[tuple[str, str, str, str, str, str]],
) -> list[dict[str, Any]]:
    """Shared core of the `(id, type, text, required, option, score)` import shape, factored out
    of `parse_rut_spt_table` so the constructor's `.xlsx` import/export (`xlsx_schema.py`) can
    feed it real spreadsheet rows instead of markdown-table lines, without duplicating the
    grouping/element-building rules below.

    One element occupies one or more consecutive rows sharing the same `id`: the first row
    carries `type`/`text`/`required` (and, for a choice-shaped question, its first option);
    every following row with the same `id` and a blank `type` adds one more option. A question
    whose `score` column is blank for every one of its options is modeled with
    `scoring_key=None` -- captured but feeding no `ResultScale` formula. Option `value`s are
    synthetic positional identifiers (`opt1`, `opt2`, ...): nothing in the domain requires them
    to be human-meaningful, and no source format used here carries a separate stable value
    column.
    """
    groups: list[tuple[str, str, str, str, list[tuple[str, str]]]] = []
    for element_id, element_type, text_cell, required_cell, option_cell, score_cell in rows:
        if element_id in ("", "ID"):
            continue
        if element_type:
            groups.append((element_id, element_type, text_cell, required_cell, []))
        elif not groups or groups[-1][0] != element_id:
            raise RutSptImportError(f"Continuation row for unknown element: {element_id!r}")
        if option_cell:
            groups[-1][4].append((option_cell, score_cell))

    elements: list[dict[str, Any]] = []
    for element_id, element_type, raw_label, required_cell, options in groups:
        required = _parse_required(required_cell)
        label = _strip_leading_number(raw_label)
        if element_type in STRUCTURAL_TYPES:
            elements.append({"key": element_id, "type": element_type, "label": label})
        elif element_type == "text":
            elements.append({"key": element_id, "type": "text", "label": label, "required": required})
        elif element_type in CHOICE_TYPES:
            elements.append(_build_choice_element(element_id, element_type, label, options, required))
        else:
            raise RutSptImportError(f"Unknown element type {element_type!r} for {element_id!r}")
    return elements


def parse_rut_spt_table(text: str) -> list[dict[str, Any]]:
    """Parse RUT's 5-column import table (markdown pipe rows) into the flat `elements` list the
    `form_tests` domain schema expects (`domain.schema.validate_test_schema`'s `elements` key).
    The source table has no `required` column, so every question comes back `required=True`."""

    def rows() -> Iterable[tuple[str, str, str, str, str, str]]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            cells = _split_row(line)
            if cells is None or len(cells) != 5:
                continue
            if all(_SEPARATOR_CELL_RE.match(cell) for cell in cells):
                continue
            yield cells[0], cells[1], cells[2], "", cells[3], cells[4]

    return build_elements_from_rows(rows())


def _build_choice_element(
    element_id: str,
    element_type: str,
    label: str,
    options: list[tuple[str, str]],
    required: bool = True,
) -> dict[str, Any]:
    if not options:
        raise RutSptImportError(f"Choice element {element_id!r} has no options")
    is_scored = any(score_cell.strip() for _, score_cell in options)
    # Strip each option's leading number only when *every* option in this question has one to
    # strip. Two real shapes in RUT's source content break that assumption and must survive
    # untouched: an endpoint/midpoint-anchored numeric scale (e.g. `"1 — Совершенно не
    # соответствует", "2", "3", "4 — Частично соответствует", ...` -- most options are bare
    # digits with no separator, so their "position" already *is* their entire label, nothing
    # redundant to derive) and Beck depression's two branching appetite/sleep items (`"1) ...",
    # "2а) ...", "2б) ...", "3а) ...", "3б) ...", ...` -- non-sequential by design, not simple
    # list position at all). Stripping only the *some* that do match would silently reintroduce
    # the exact "position 2 renders as 2 but options[1] is really '2а'" mismatch this exists to
    # avoid, so an all-or-nothing per-question check is required, not a per-option one.
    strip_options = all(_strip_leading_number(option_label) != option_label for option_label, _ in options)
    normalized_options = [
        {
            "value": f"opt{index + 1}",
            "label": _strip_leading_number(option_label) if strip_options else option_label,
            "score": float(score_cell) if score_cell.strip() else 0.0,
        }
        for index, (option_label, score_cell) in enumerate(options)
    ]
    return {
        "key": element_id,
        "type": element_type,
        "label": label,
        "required": required,
        "scoring_key": element_id if is_scored else None,
        "options": normalized_options,
    }


def load_rut_spt_elements(path: str | Path) -> list[dict[str, Any]]:
    return parse_rut_spt_table(Path(path).read_text(encoding="utf-8"))
