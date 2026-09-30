import type { FormFieldType } from "@/entities/form/model/types";

export const FORM_FIELD_TYPES: ReadonlyArray<{
  value: FormFieldType;
  label: string;
}> = [
  { value: "short_text", label: "Короткий текст" },
  { value: "long_text", label: "Длинный текст" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Телефон" },
  { value: "number", label: "Число" },
  { value: "date", label: "Дата" },
  { value: "checkbox", label: "Чекбокс" },
  { value: "select", label: "Выпадающий список" },
  { value: "radio", label: "Один вариант" },
  { value: "multiselect", label: "Мультивыбор (чекбоксы)" },
  { value: "file", label: "Файл" },
];

export function formFieldTypeLabel(type: FormFieldType): string {
  return FORM_FIELD_TYPES.find((item) => item.value === type)?.label ?? type;
}
