from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .rut_spt_import import RutSptImportError, build_elements_from_rows

INFO_SHEET = "Тест"
ELEMENTS_SHEET = "Элементы"
SCALES_SHEET = "Шкалы"
FILTERS_SHEET = "Фильтры"
TEMPLATE_SHEET = "Шаблон"

_ELEMENTS_HEADER = ["ID", "Тип элемента", "Текст", "Обязательный", "Вариант ответа", "Балл"]
_SCALES_HEADER = ["Ключ", "Название", "Термы", "Константа", "Агрегация"]
_FILTERS_HEADER = ["Шкала", "От", "До", "Метка", "Риск", "Рекомендация"]

_REQUIRED_SHEETS = {INFO_SHEET, ELEMENTS_SHEET, SCALES_SHEET, FILTERS_SHEET, TEMPLATE_SHEET}


class XlsxSchemaError(ValueError):
    """The uploaded workbook doesn't match the constructor's export shape -- missing a sheet,
    a wrong header row, or a value that doesn't parse -- surfaced to the admin as `bad_request`
    the same way a malformed hand-typed schema already is (see `admin_router._raise_admin_test_error`)."""


def _cell(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _term_string(terms: list[dict[str, Any]]) -> str:
    parts = []
    for term in terms:
        key = term.get("question_key") or term.get("result_scale_key")
        sign = "+" if term["weight"] >= 0 else "-"
        parts.append(f"{key}:{sign}{abs(term['weight']):g}")
    return "; ".join(parts)


def _parse_terms(value: str, scoring_keys: set[str]) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    for chunk in value.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise XlsxSchemaError(f"Term {chunk!r} must be formatted as key:+1 or key:-1")
        key, weight_raw = chunk.rsplit(":", 1)
        key = key.strip()
        weight_raw = weight_raw.strip()
        if weight_raw not in {"+1", "-1", "1"}:
            raise XlsxSchemaError(f"Term weight must be +1 or -1, got {weight_raw!r} for {key!r}")
        weight = -1.0 if weight_raw.startswith("-") else 1.0
        is_scale = key not in scoring_keys
        terms.append(
            {
                "question_key": None if is_scale else key,
                "result_scale_key": key if is_scale else None,
                "weight": weight,
            }
        )
    return terms


def write_schema_workbook(*, name: str, intro_text: str | None, schema: dict[str, Any]) -> Workbook:
    """Mirrors `read_schema_workbook`: five sheets an admin can open in Excel, hand-edit, and
    re-upload -- the elements sheet is exactly RUT's own 5-column import shape (Task 068) plus one
    `Обязательный` column, so a real RUT-style questionnaire table pastes in directly."""
    workbook = Workbook()
    info_sheet = workbook.active
    info_sheet.title = INFO_SHEET
    info_sheet.append(["Название", name])
    info_sheet.append(["Вводный текст", intro_text or ""])

    elements_sheet = workbook.create_sheet(ELEMENTS_SHEET)
    elements_sheet.append(_ELEMENTS_HEADER)
    for element in schema["elements"]:
        _write_element_rows(elements_sheet, element)

    scales_sheet = workbook.create_sheet(SCALES_SHEET)
    scales_sheet.append(_SCALES_HEADER)
    for scale in schema["result_scales"]:
        scales_sheet.append(
            [scale["key"], scale["label"], _term_string(scale["terms"]), scale["constant"], scale["aggregation"]]
        )

    filters_sheet = workbook.create_sheet(FILTERS_SHEET)
    filters_sheet.append(_FILTERS_HEADER)
    for filt in schema["filters"]:
        for rule in filt["rules"]:
            filters_sheet.append(
                [
                    filt["result_scale_key"],
                    rule["min"],
                    rule["max"],
                    rule["label"],
                    "TRUE" if rule["is_flagged"] else "FALSE",
                    rule.get("recommendation_text") or "",
                ]
            )

    template_sheet = workbook.create_sheet(TEMPLATE_SHEET)
    template_sheet.append(["Шаблон сообщения"])
    template_sheet.append([schema["result_template"]])

    return workbook


def _write_element_rows(sheet: Worksheet, element: dict[str, Any]) -> None:
    key, etype, label = element["key"], element["type"], element["label"]
    required = "TRUE" if element.get("required") else "FALSE"
    options = element.get("options")
    if not options:
        sheet.append([key, etype, label, required if "required" in element else "", "", ""])
        return
    scored = bool(element.get("scoring_key"))
    for index, option in enumerate(options):
        score = option["score"] if scored else ""
        if index == 0:
            sheet.append([key, etype, label, required, option["label"], score])
        else:
            sheet.append([key, "", "", "", option["label"], score])


def read_schema_workbook(data: bytes) -> dict[str, Any]:
    """Inverse of `write_schema_workbook`. Raises `XlsxSchemaError` for anything structurally
    wrong; per-value domain validation (unknown key references, invalid ranges, ...) is left to
    the caller's usual `validate_test_schema`/`validate_test_schema_draft` pass, exactly as a
    hand-typed draft save already goes through -- this function's job is only "turn the workbook
    into the same raw dict shape a PUT .../draft body already carries", not to re-implement that
    validation a second time."""
    try:
        workbook = load_workbook(BytesIO(data), data_only=True)
    except Exception as exc:  # noqa: BLE001 -- openpyxl raises several distinct exception types for a corrupt file
        raise XlsxSchemaError("Uploaded file is not a valid .xlsx workbook") from exc

    missing = _REQUIRED_SHEETS - set(workbook.sheetnames)
    if missing:
        raise XlsxSchemaError(f"Workbook is missing sheet(s): {', '.join(sorted(missing))}")

    name, intro_text = _read_info_sheet(workbook[INFO_SHEET])
    elements = _read_elements_sheet(workbook[ELEMENTS_SHEET])
    scoring_keys = {element["scoring_key"] for element in elements if element.get("scoring_key")}
    result_scales = _read_scales_sheet(workbook[SCALES_SHEET], scoring_keys)
    filters = _read_filters_sheet(workbook[FILTERS_SHEET])
    result_template = _read_template_sheet(workbook[TEMPLATE_SHEET])

    return {
        "name": name,
        "intro_text": intro_text,
        "test_schema": {
            "elements": elements,
            "result_scales": result_scales,
            "filters": filters,
            "result_template": result_template,
        },
    }


def _read_info_sheet(sheet: Worksheet) -> tuple[str, str | None]:
    # Only the row label (`row[0]`, e.g. "Название") goes through `_cell`'s `.strip()` -- it's a
    # fixed lookup key, not admin content. The value (`row[1]`) is read raw: `name` is a single-
    # line field where trimming stray whitespace is harmless, but `intro_text` is free-form
    # multi-line text where a leading/trailing blank line is meaningful admin-authored spacing,
    # not incidental padding -- the same distinction `_read_template_sheet` makes below.
    values = {_cell(row[0]): (row[1] if len(row) > 1 else None) for row in sheet.iter_rows(values_only=True)}
    name = _cell(values.get("Название"))
    intro_raw = values.get("Вводный текст")
    intro_text = "" if intro_raw is None else str(intro_raw)
    return name, (intro_text or None)


def _read_elements_sheet(sheet: Worksheet) -> list[dict[str, Any]]:
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    normalized = (
        (_cell(row[0]), _cell(row[1]), _cell(row[2]), _cell(row[3]), _cell(row[4]), _cell(row[5]))
        for row in rows
        if row and any(_cell(cell) for cell in row)
    )
    try:
        return build_elements_from_rows(normalized)
    except RutSptImportError as exc:
        raise XlsxSchemaError(str(exc)) from exc


def _read_scales_sheet(sheet: Worksheet, scoring_keys: set[str]) -> list[dict[str, Any]]:
    result_scales: list[dict[str, Any]] = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or not any(_cell(cell) for cell in row):
            continue
        key, label, terms_cell, constant_cell, aggregation = (
            _cell(row[0]),
            _cell(row[1]),
            _cell(row[2]),
            _cell(row[3]),
            _cell(row[4]),
        )
        if not key:
            continue
        try:
            constant = float(constant_cell) if constant_cell else 0.0
        except ValueError as exc:
            raise XlsxSchemaError(f"Scale {key!r}: constant must be a number, got {constant_cell!r}") from exc
        # `_parse_terms` only needs to tell "this term is a question" from "this term is
        # another scale" -- it doesn't need to know the other scale actually exists (forward
        # references to a scale defined later in this same sheet are fine); real existence and
        # cycle checks happen when the returned dict goes through `validate_test_schema[_draft]`,
        # exactly like a hand-typed draft save already does.
        result_scales.append(
            {
                "key": key,
                "label": label,
                "terms": _parse_terms(terms_cell, scoring_keys),
                "constant": constant,
                "aggregation": aggregation or "sum",
            }
        )
    return result_scales


def _read_filters_sheet(sheet: Worksheet) -> list[dict[str, Any]]:
    rules_by_scale: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or not any(_cell(cell) for cell in row):
            continue
        scale_key = _cell(row[0])
        if not scale_key:
            continue
        min_cell, max_cell, label, flagged_cell, recommendation = (
            _cell(row[1]),
            _cell(row[2]),
            _cell(row[3]),
            _cell(row[4]),
            _cell(row[5]),
        )
        if scale_key not in rules_by_scale:
            rules_by_scale[scale_key] = []
            order.append(scale_key)
        rules_by_scale[scale_key].append(
            {
                "min": float(min_cell) if min_cell else None,
                "max": float(max_cell) if max_cell else None,
                "label": label,
                "is_flagged": flagged_cell.strip().lower() in {"true", "1", "да", "yes"},
                "recommendation_text": recommendation or None,
            }
        )
    return [{"result_scale_key": key, "rules": rules_by_scale[key]} for key in order]


def _read_template_sheet(sheet: Worksheet) -> str:
    # Deliberately not `_cell()` (which `.strip()`s): a leading/trailing blank line in the result
    # message template is admin-authored spacing in what the student ultimately reads, not
    # incidental whitespace to trim -- losing it on import is a silent content change, exactly
    # the class of bug `read_schema_workbook`'s "inverse of `write_schema_workbook`" contract
    # exists to rule out.
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    if not rows or rows[0][0] is None:
        return ""
    return str(rows[0][0])
