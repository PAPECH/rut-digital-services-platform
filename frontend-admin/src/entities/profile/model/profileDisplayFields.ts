import type { ProfileFieldDefinition } from "@/api/types";

export interface ProfileDisplayField {
  key: string;
  label: string;
  type: ProfileFieldDefinition["type"] | "full_name";
  source: "platform" | "bot";
}

export const DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS = [
  "full_name",
  "phone",
  "email",
  "birth_date",
] as const;

const PLATFORM_PROFILE_FIELDS: ProfileDisplayField[] = [
  { key: "full_name", label: "ФИО", type: "full_name", source: "platform" },
  { key: "phone", label: "Телефон", type: "phone", source: "platform" },
  { key: "email", label: "Почта", type: "email", source: "platform" },
  { key: "birth_date", label: "Дата рождения", type: "date", source: "platform" },
];

const PLATFORM_PROFILE_KEYS = new Set(
  PLATFORM_PROFILE_FIELDS.map((field) => field.key),
);

export function availableProfileDisplayFields(
  profileSchema: ProfileFieldDefinition[],
): ProfileDisplayField[] {
  const custom = profileSchema
    .filter((field) => !PLATFORM_PROFILE_KEYS.has(field.key))
    .map((field): ProfileDisplayField => ({
      key: field.key,
      label: field.label,
      type: field.type,
      source: "bot",
    }));
  return [...PLATFORM_PROFILE_FIELDS, ...custom];
}
