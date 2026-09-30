import type { FormTestElementType } from "@/entities/form-test/model/types";

export const STRUCTURAL_ELEMENT_TYPES: { value: FormTestElementType; label: string }[] = [
  { value: "questionnaire_title", label: "Заголовок методики" },
  { value: "section_title", label: "Заголовок раздела" },
  { value: "instruction", label: "Текст инструкции" },
];

export const QUESTION_ELEMENT_TYPES: { value: FormTestElementType; label: string }[] = [
  { value: "text", label: "Текстовый ответ" },
  { value: "single_choice", label: "Один вариант" },
  { value: "multiple_choice", label: "Несколько вариантов" },
  { value: "scale", label: "Шкала (рейтинг)" },
];

export const ELEMENT_TYPES = [...STRUCTURAL_ELEMENT_TYPES, ...QUESTION_ELEMENT_TYPES];

export const CHOICE_ELEMENT_TYPES = new Set<FormTestElementType>([
  "single_choice",
  "multiple_choice",
  "scale",
]);

export const STRUCTURAL_ELEMENT_TYPE_SET = new Set<FormTestElementType>(
  STRUCTURAL_ELEMENT_TYPES.map((type) => type.value),
);

export function elementTypeLabel(type: FormTestElementType): string {
  return ELEMENT_TYPES.find((item) => item.value === type)?.label ?? type;
}
