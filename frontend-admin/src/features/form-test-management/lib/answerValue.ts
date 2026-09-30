import type { FormTestElement, FormTestElementType } from "@/entities/form-test/model/types";

export const ANSWERABLE_ELEMENT_TYPES: ReadonlySet<FormTestElementType> = new Set([
  "text",
  "single_choice",
  "multiple_choice",
  "scale",
]);

export function answerableElements(elements: FormTestElement[]): FormTestElement[] {
  return elements.filter((element) => ANSWERABLE_ELEMENT_TYPES.has(element.type));
}

/** One running count across the whole test, never resetting at a section/part boundary --
 * mirrors the mini-app's identical `numberElements` (`frontend-miniapp/src/features/form-tests/
 * model/numbering.ts`) so a question's number matches between what the student saw and what the
 * admin sees in results/export. Question numbers used to be hand-typed into every `label`; now
 * computed here instead so reordering/inserting/deleting a question never leaves a stale one. */
export function numberElements(elements: FormTestElement[]): Map<string, number> {
  const numbers = new Map<string, number>();
  let n = 0;
  for (const element of elements) {
    if (!ANSWERABLE_ELEMENT_TYPES.has(element.type)) continue;
    n += 1;
    numbers.set(element.key, n);
  }
  return numbers;
}

export type AttemptValueMode = "text" | "score";

function optionLabel(element: FormTestElement, value: string): string {
  return element.options?.find((option) => option.value === value)?.label ?? value;
}

function optionScore(element: FormTestElement, value: string): number | undefined {
  return element.options?.find((option) => option.value === value)?.score;
}

export function answerTextValue(element: FormTestElement, answers: Record<string, unknown>): string {
  const raw = answers[element.key];
  if (raw === null || raw === undefined || raw === "") return "";
  if (element.type === "text") return String(raw);
  if (element.type === "multiple_choice" && Array.isArray(raw)) {
    return raw.map((value) => optionLabel(element, String(value))).join(", ");
  }
  return optionLabel(element, String(raw));
}

/** Mirrors the backend's `xlsx_export.py::_answer_score_value` -- `null` for a `text` question
 * (nothing to score), an unanswered one, or one with no `scoring_key`. The `scoring_key` check
 * matters even though every choice question's options always carry a `score` field: an
 * anketa/demographic question never wired into any formula still has each option's `score`
 * filled in as unused boilerplate, which must not be shown as a meaningful score. */
export function answerScoreValue(element: FormTestElement, answers: Record<string, unknown>): number | null {
  if (
    (element.type !== "single_choice" && element.type !== "multiple_choice" && element.type !== "scale") ||
    !element.scoring_key
  ) {
    return null;
  }
  const raw = answers[element.key];
  if (raw === null || raw === undefined) return null;
  if (element.type === "multiple_choice" && Array.isArray(raw)) {
    const scores = raw
      .map((value) => optionScore(element, String(value)))
      .filter((score): score is number => score !== undefined);
    return scores.length ? scores.reduce((sum, score) => sum + score, 0) : null;
  }
  return optionScore(element, String(raw)) ?? null;
}

/** `mode="score"` shows the numeric score for a scored choice question; a `text` question (or an
 * unanswered one) always falls back to its text value -- there is no score to show for it
 * regardless of the requested mode, matching the backend export's resolution rule exactly. */
export function answerDisplayValue(
  element: FormTestElement,
  answers: Record<string, unknown>,
  mode: AttemptValueMode,
): string {
  if (mode === "score") {
    const score = answerScoreValue(element, answers);
    if (score !== null) return String(score);
  }
  const text = answerTextValue(element, answers);
  return text || "—";
}
