from __future__ import annotations

from datetime import date
from typing import Any, Literal

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ..domain.entities import TestAttempt

ValueMode = Literal["text", "score"]

_IDENTITY_HEADERS = ("Фамилия", "Имя", "Отчество", "Дата рождения", "Email")
_IDENTITY_KEYS = ("last_name", "first_name", "patronymic", "birth_date", "email")


def _identity_row(attempt: TestAttempt, fallback_identities: dict[int, dict[str, Any]]) -> list[Any]:
    """The RUT SPT anketa no longer asks the student for name/birth date/email itself (Task 080)
    -- these come from `identity_snapshot`, frozen once at completion so a later profile edit can
    never retroactively change what an already-completed attempt reports. Attempts completed
    before this shipped have no snapshot; `fallback_identities` (a live profile lookup, built by
    the caller for exactly those attempts) fills the gap so no export row is ever blank."""
    data = attempt.identity_snapshot or fallback_identities.get(attempt.user_id) or {}
    birth_date = data.get("birth_date")
    if isinstance(birth_date, str):
        birth_date = date.fromisoformat(birth_date)
    return [data.get(key) if key != "birth_date" else birth_date for key in _IDENTITY_KEYS]


def _answerable_elements(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Every question a student could answer, scored or not (Task 077 widened this beyond Task
    068's original unscored-only column set now that `value_mode` lets an admin choose text or
    score per column instead of the export silently omitting scored questions)."""
    return [
        element
        for element in schema["elements"]
        if element["type"] in {"text", "single_choice", "multiple_choice", "scale"}
    ]


def _element_numbers(schema: dict[str, Any]) -> dict[str, int]:
    """One running count across the whole test, never resetting at a section/part boundary --
    mirrors the frontends' identical `numberElements` (`frontend-miniapp/src/features/form-tests/
    model/numbering.ts`, `frontend-admin/src/features/form-test-management/lib/answerValue.ts`)
    so a question's number in the export matches what the student and the admin both see."""
    numbers: dict[str, int] = {}
    n = 0
    for element in schema["elements"]:
        if element["type"] not in {"text", "single_choice", "multiple_choice", "scale"}:
            continue
        n += 1
        numbers[element["key"]] = n
    return numbers


def _answer_text_value(element: dict[str, Any], answers: dict[str, Any]) -> str:
    raw = answers.get(element["key"])
    if raw is None:
        return ""
    if element["type"] == "text":
        return str(raw)
    options_by_value = {option["value"]: option["label"] for option in element.get("options", [])}
    if element["type"] == "multiple_choice":
        return ", ".join(options_by_value.get(value, value) for value in raw)
    return options_by_value.get(raw, str(raw))


def _answer_score_value(element: dict[str, Any], answers: dict[str, Any]) -> float | None:
    """The numeric score this element's answer contributes, mirroring
    `domain.scoring.compute_question_scores` -- `None` for a `text` question (nothing to score),
    an unanswered one, or one with no `scoring_key`. That last case matters even though every
    choice question's options always carry a `score` field regardless of `scoring_key`
    (Task 068's schema shape): an anketa/demographic question RUT never wired into any formula
    (e.g. "Вы обучаетесь на: Бюджете/Платном/Целевом") still has each option's `score` filled in
    as unused boilerplate (observed as a flat `0.0` on every option against the live RUT SPT seed)
    -- showing that would misrepresent an arbitrary placeholder as a meaningful score."""
    if element["type"] not in {"single_choice", "multiple_choice", "scale"} or not element.get("scoring_key"):
        return None
    raw = answers.get(element["key"])
    if raw is None:
        return None
    option_scores = {option["value"]: option["score"] for option in element.get("options", [])}
    if element["type"] == "multiple_choice":
        return sum(option_scores[value] for value in raw if value in option_scores)
    return option_scores.get(raw)


def _answer_export_value(element: dict[str, Any], answers: dict[str, Any], value_mode: ValueMode) -> Any:
    """`value_mode="score"` shows the numeric score for a scored choice question; a `text`
    question (or an unanswered one) always falls back to its text value -- there is no score to
    show for it regardless of the requested mode (Task 077's confirmed resolution rule)."""
    if value_mode == "score":
        score = _answer_score_value(element, answers)
        if score is not None:
            return score
    return _answer_text_value(element, answers)


def build_attempts_workbook(
    schema: dict[str, Any],
    attempts: list[TestAttempt],
    *,
    value_mode: ValueMode = "text",
    fallback_identities: dict[int, dict[str, Any]] | None = None,
) -> Workbook:
    """One row per completed attempt: the respondent's identity (Task 080 -- last name/first name/
    patronymic/birth date/email, sourced from the profile rather than test answers), the student's
    own answer to every question (as text or as its numeric score, per `value_mode` -- Task 077
    reverses Task 068's original "never include a scored question's raw answer" posture per the
    requester's confirmed decision), followed by every `ResultScale`'s computed value and matched
    filter label, and attempt timestamps -- see Task 068's API contract for the export shape this
    extends. `fallback_identities` (keyed by `user_id`) fills in the identity columns for an
    attempt completed before Task 080 shipped, which has no frozen `identity_snapshot` of its own;
    the caller (`presentation.admin_router`) builds it from a live profile lookup for exactly the
    attempts that need it."""
    workbook = Workbook()
    sheet: Worksheet = workbook.active
    sheet.title = "Attempts"

    elements = _answerable_elements(schema)
    numbers = _element_numbers(schema)
    result_scales = schema["result_scales"]
    fallback_identities = fallback_identities or {}

    headers = [
        "ID попытки",
        "ID пользователя",
        *_IDENTITY_HEADERS,
        "Начата",
        "Завершена",
        "Согласие получено",
        "Дата согласия",
    ]
    headers += [f"{numbers[element['key']]}) {element['label']}" for element in elements]
    for scale in result_scales:
        headers += [f"{scale['label']} — значение", f"{scale['label']} — интерпретация"]
    sheet.append(headers)

    for attempt in attempts:
        row: list[Any] = [
            attempt.id,
            attempt.user_id,
            *_identity_row(attempt, fallback_identities),
            attempt.started_at.replace(tzinfo=None) if attempt.started_at else None,
            attempt.completed_at.replace(tzinfo=None) if attempt.completed_at else None,
            "да" if attempt.consent_accepted else "нет",
            attempt.consent_accepted_at.replace(tzinfo=None) if attempt.consent_accepted_at else None,
        ]
        row += [_answer_export_value(element, attempt.answers, value_mode) for element in elements]
        computed = attempt.computed_results or {}
        for scale in result_scales:
            entry = computed.get(scale["key"])
            if entry is None:
                row += [None, None]
                continue
            filt = entry.get("filter")
            row += [entry.get("value"), filt.get("label") if filt else None]
        sheet.append(row)

    return workbook
