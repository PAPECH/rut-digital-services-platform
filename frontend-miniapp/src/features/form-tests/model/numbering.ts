import type { FormTestElement } from "@/entities/form-test/model/types";

const STRUCTURAL_TYPES = new Set<FormTestElement["type"]>([
  "questionnaire_title",
  "section_title",
  "instruction",
]);

/** One running count across the whole test, never resetting at a section/part boundary
 * (confirmed product decision, Task 079) -- a student always sees "question 47", not a count
 * that restarts at 1 inside every instrument. Question numbers used to be hand-typed into every
 * `label` (`"1) Ваша фамилия"`); they're computed here instead so reordering/inserting/deleting a
 * question can never leave a stale number behind. */
export function numberElements(elements: FormTestElement[]): Map<string, number> {
  const numbers = new Map<string, number>();
  let n = 0;
  for (const element of elements) {
    if (STRUCTURAL_TYPES.has(element.type)) continue;
    n += 1;
    numbers.set(element.key, n);
  }
  return numbers;
}
