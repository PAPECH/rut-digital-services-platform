import type { FormField } from "@/entities/form/model/types";
import type { Profile } from "@/api/types";

export function initialFormValue(
  field: FormField,
  profile: Profile | null,
): unknown {
  if (field.profile_key && profile) {
    const direct = (profile as unknown as Record<string, unknown>)[
      field.profile_key
    ];
    const shared = profile.shared_data?.[field.profile_key];
    const local = profile.local_data?.[field.profile_key];
    const value = direct ?? shared ?? local;
    if (value !== null && value !== undefined && value !== "") return value;
  }
  if (
    "default" in field &&
    field.default !== null &&
    field.default !== undefined
  )
    return field.default;
  if (field.type === "file" || field.type === "multiselect") return [];
  return "";
}

function empty(value: unknown): boolean {
  return (
    value === null ||
    value === undefined ||
    value === "" ||
    (Array.isArray(value) && value.length === 0)
  );
}

export function validateFormValue(
  field: FormField,
  value: unknown,
): string | null {
  if (
    field.required &&
    (empty(value) || (field.type === "checkbox" && value !== true))
  )
    return `Заполните поле «${field.label}»`;
  if (field.type === "multiselect") {
    const values = Array.isArray(value) ? value : [];
    const allowed = new Set(field.options.map((option) => option.value));
    if (values.some((v) => typeof v !== "string" || !allowed.has(v)))
      return `Выберите вариант из списка в поле «${field.label}»`;
    const min = field.required
      ? Math.max(field.min_selected ?? 0, 1)
      : (field.min_selected ?? 0);
    const max = field.max_selected ?? field.options.length;
    if (values.length < min)
      return `Выберите не менее ${min} вариант(ов) в поле «${field.label}»`;
    if (values.length > max)
      return `Выберите не более ${max} вариант(ов) в поле «${field.label}»`;
    return null;
  }
  if (empty(value)) return null;
  if (field.type === "short_text" || field.type === "long_text") {
    const text = String(value);
    if (text.length < field.min_length || text.length > field.max_length)
      return `Проверьте длину поля «${field.label}»`;
    if (field.type === "short_text" && field.pattern) {
      try {
        if (!new RegExp(`^(?:${field.pattern})$`).test(text))
          return `Проверьте формат поля «${field.label}»`;
      } catch {
        /* server validates the configured expression */
      }
    }
  }
  if (
    field.type === "email" &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))
  )
    return `Укажите корректный email в поле «${field.label}»`;
  if (field.type === "phone" && field.pattern) {
    try {
      if (!new RegExp(`^(?:${field.pattern})$`).test(String(value)))
        return `Проверьте телефон в поле «${field.label}»`;
    } catch {
      /* server validates */
    }
  }
  if (field.type === "number") {
    const number = Number(value);
    if (!Number.isFinite(number))
      return `Укажите число в поле «${field.label}»`;
    if (field.min !== null && number < field.min)
      return `Минимум для «${field.label}»: ${field.min}`;
    if (field.max !== null && number > field.max)
      return `Максимум для «${field.label}»: ${field.max}`;
  }
  if (field.type === "date") {
    const date = String(value);
    if (field.min && date < field.min)
      return `Минимальная дата для «${field.label}»: ${field.min}`;
    if (field.max && date > field.max)
      return `Максимальная дата для «${field.label}»: ${field.max}`;
  }
  if (
    (field.type === "select" || field.type === "radio") &&
    !field.options.some((option) => option.value === value)
  )
    return `Выберите вариант в поле «${field.label}»`;
  if (
    field.type === "file" &&
    (!Array.isArray(value) || value.length > field.max_files)
  )
    return `Проверьте файлы в поле «${field.label}»`;
  return null;
}
