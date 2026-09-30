import type {
  FormTestElement,
  FormTestElementType,
} from "@/entities/form-test/model/types";
import { CHOICE_ELEMENT_TYPES, STRUCTURAL_ELEMENT_TYPE_SET } from "@/features/form-test-management/model/elementTypes";

function uniqueKey(prefix: string, existing: FormTestElement[]): string {
  const used = new Set(existing.map((element) => element.key));
  let index = existing.length + 1;
  let key = `${prefix}_${index}`;
  while (used.has(key)) {
    index += 1;
    key = `${prefix}_${index}`;
  }
  return key;
}

export function createElement(
  type: FormTestElementType,
  existing: FormTestElement[],
): FormTestElement {
  const key = uniqueKey(type, existing);
  const base: FormTestElement = { key, type, label: "" };
  if (STRUCTURAL_ELEMENT_TYPE_SET.has(type)) return base;
  const question: FormTestElement = { ...base, required: false, scoring_key: null };
  if (CHOICE_ELEMENT_TYPES.has(type)) {
    return { ...question, options: [] };
  }
  return question;
}

export function convertElementType(
  element: FormTestElement,
  type: FormTestElementType,
): FormTestElement {
  if (STRUCTURAL_ELEMENT_TYPE_SET.has(type)) {
    return { key: element.key, type, label: element.label };
  }
  const question: FormTestElement = {
    key: element.key,
    type,
    label: element.label,
    required: element.required ?? false,
    scoring_key: element.scoring_key ?? null,
  };
  if (CHOICE_ELEMENT_TYPES.has(type)) {
    return { ...question, options: element.options ?? [] };
  }
  return question;
}

export function duplicateElement(
  element: FormTestElement,
  existing: FormTestElement[],
): FormTestElement {
  return { ...element, key: uniqueKey(element.type, existing) };
}
