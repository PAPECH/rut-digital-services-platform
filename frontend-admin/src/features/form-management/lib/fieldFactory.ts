import type { FormField, FormFieldType } from "@/entities/form/model/types";

function key(): string {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replaceAll("-", "").slice(0, 12)
      : `${Date.now()}${Math.floor(Math.random() * 1_000)}`;
  return `field_${suffix}`;
}

const base = (type: FormFieldType) => ({
  key: key(),
  type,
  label: "Новое поле",
  help_text: null,
  required: false,
  active: true,
  profile_key: null,
});

export function createFormField(type: FormFieldType): FormField {
  const common = base(type);
  switch (type) {
    case "short_text":
      return {
        ...common,
        type,
        placeholder: null,
        default: null,
        min_length: 0,
        max_length: 20_000,
        pattern: null,
      };
    case "long_text":
      return {
        ...common,
        type,
        placeholder: null,
        default: null,
        min_length: 0,
        max_length: 20_000,
      };
    case "email":
      return { ...common, type, placeholder: null, default: null };
    case "phone":
      return {
        ...common,
        type,
        placeholder: null,
        default: null,
        pattern: null,
      };
    case "number":
      return {
        ...common,
        type,
        placeholder: null,
        default: null,
        min: null,
        max: null,
        step: 1,
      };
    case "date":
      return { ...common, type, default: null, min: null, max: null };
    case "checkbox":
      return { ...common, type, default: false };
    case "select":
      return {
        ...common,
        type,
        options: [{ value: "option_1", label: "Вариант 1" }],
        default: null,
      };
    case "radio":
      return {
        ...common,
        type,
        options: [{ value: "option_1", label: "Вариант 1" }],
        default: null,
      };
    case "multiselect":
      return {
        ...common,
        type,
        options: [{ value: "option_1", label: "Вариант 1" }],
        default: null,
        min_selected: null,
        max_selected: null,
      };
    case "file":
      return {
        ...common,
        type,
        accepted_mime_types: [],
        max_files: 1,
        max_size_bytes: 20 * 1024 * 1024,
      };
  }
}

export function convertFormFieldType(
  field: FormField,
  type: FormFieldType,
): FormField {
  if (field.type === type) return field;
  const converted = createFormField(type);
  return {
    ...converted,
    key: field.key,
    label: field.label,
    help_text: field.help_text,
    required: field.required,
    active: field.active,
    profile_key: field.profile_key,
  } as FormField;
}
