import type { FormTestElement } from "@/entities/form-test/model/types";

export interface SingleElementGroup {
  kind: "single";
  element: FormTestElement;
}

export interface ScaleMatrixGroup {
  kind: "scale_matrix";
  /** Shared option labels every question in the group renders as column headers. */
  optionLabels: string[];
  questions: FormTestElement[];
}

export type ElementGroup = SingleElementGroup | ScaleMatrixGroup;

const STRUCTURAL_ELEMENT_TYPES = new Set<FormTestElement["type"]>([
  "questionnaire_title",
  "section_title",
  "instruction",
]);

/** Whether a group is an answerable question (vs. a display-only structural element) -- used to
 * place a divider strictly between two consecutive questions, never around a title/instruction,
 * which already reads as its own section break. */
export function isQuestionGroup(group: ElementGroup): boolean {
  return group.kind === "scale_matrix" || !STRUCTURAL_ELEMENT_TYPES.has(group.element.type);
}

function optionLabelsKey(element: FormTestElement): string {
  return (element.options ?? []).map((option) => option.label).join("|");
}

/**
 * Consecutive `scale` questions that share the same option labels are how 7 of the 8 source
 * psychometric instruments are actually laid out (Spielberger-Khanin, academic motivation,
 * socio-cultural environment, BAT, basic needs, SURPS, Buss-Perry) -- group them into one
 * rating-row matrix instead of repeating the same option list under every statement. A run
 * breaks on a type change or a different option set, matching the backend plan's contract.
 */
export function groupElements(elements: FormTestElement[]): ElementGroup[] {
  const groups: ElementGroup[] = [];
  let index = 0;
  while (index < elements.length) {
    const element = elements[index];
    if (element.type !== "scale" || !element.options?.length) {
      groups.push({ kind: "single", element });
      index += 1;
      continue;
    }
    const key = optionLabelsKey(element);
    const run: FormTestElement[] = [element];
    let lookahead = index + 1;
    while (
      lookahead < elements.length &&
      elements[lookahead].type === "scale" &&
      optionLabelsKey(elements[lookahead]) === key
    ) {
      run.push(elements[lookahead]);
      lookahead += 1;
    }
    groups.push({
      kind: "scale_matrix",
      optionLabels: element.options.map((option) => option.label),
      questions: run,
    });
    index = lookahead;
  }
  return groups;
}
