from __future__ import annotations

from app.modules.form_tests.infrastructure.rut_spt_import import build_elements_from_rows

_ROW = tuple[str, str, str, str, str, str]


def _rows(*rows: _ROW) -> list[_ROW]:
    return list(rows)


def test_strips_leading_number_from_question_label() -> None:
    elements = build_elements_from_rows(
        _rows(("Q1", "text", "1) Ваша фамилия", "", "", ""))
    )
    assert elements[0]["label"] == "Ваша фамилия"


def test_strips_leading_number_with_dash_separator() -> None:
    elements = build_elements_from_rows(
        _rows(("Q1", "text", "13 — Уровень стресса", "", "", ""))
    )
    assert elements[0]["label"] == "Уровень стресса"


def test_strips_leading_number_from_every_option_when_all_match() -> None:
    elements = build_elements_from_rows(
        _rows(
            ("Q1", "single_choice", "1) Ваш пол", "", "1) Мужской", ""),
            ("Q1", "", "", "", "2) Женский", ""),
        )
    )
    assert [o["label"] for o in elements[0]["options"]] == ["Мужской", "Женский"]


def test_leaves_options_untouched_when_endpoints_only_are_anchored() -> None:
    """A 1-7 scale where only the endpoints/midpoint carry text (`"2"`, `"3"`, `"5"`, `"6"` are
    bare digits with no separator) must not be touched at all: the bare digits already *are*
    their complete label, and partially stripping only the anchored ones would leave the client
    unable to tell "already just the number" apart from "still needs a number prepended"."""
    elements = build_elements_from_rows(
        _rows(
            ("Q1", "scale", "1) Насколько это про вас", "", "1 — Совсем не соответствует", ""),
            ("Q1", "", "", "", "2", ""),
            ("Q1", "", "", "", "3", ""),
            ("Q1", "", "", "", "4 — Частично соответствует", ""),
            ("Q1", "", "", "", "5", ""),
            ("Q1", "", "", "", "6", ""),
            ("Q1", "", "", "", "7 — Полностью соответствует", ""),
        )
    )
    assert [o["label"] for o in elements[0]["options"]] == [
        "1 — Совсем не соответствует",
        "2",
        "3",
        "4 — Частично соответствует",
        "5",
        "6",
        "7 — Полностью соответствует",
    ]


def test_leaves_options_untouched_for_non_sequential_branching_labels() -> None:
    """Beck depression's appetite/sleep items branch into "a"/"b" variants at the same severity
    level (`"2а)"`, `"2б)"`) -- not simple list position, so must survive verbatim rather than
    being reinterpreted as sequential."""
    elements = build_elements_from_rows(
        _rows(
            ("Q1", "single_choice", "15) Аппетит", "", "1) Мой аппетит не изменился", ""),
            ("Q1", "", "", "", "2а) Аппетит снижен", ""),
            ("Q1", "", "", "", "2б) Аппетит повышен", ""),
        )
    )
    assert [o["label"] for o in elements[0]["options"]] == [
        "1) Мой аппетит не изменился",
        "2а) Аппетит снижен",
        "2б) Аппетит повышен",
    ]


def test_structural_element_label_without_a_number_is_unaffected() -> None:
    elements = build_elements_from_rows(
        _rows(("TITLE", "questionnaire_title", "Анкета", "", "", ""))
    )
    assert elements[0]["label"] == "Анкета"
