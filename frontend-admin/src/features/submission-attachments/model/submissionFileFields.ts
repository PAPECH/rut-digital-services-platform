import type { FormField } from "@/entities/form/model/types";

function snapshotFields(formSnapshot: Record<string, unknown>): unknown[] {
  return Array.isArray(formSnapshot.fields) ? formSnapshot.fields : [];
}

export function submissionFileFieldKeys(
  formSnapshot: Record<string, unknown>,
  currentFields: FormField[],
): ReadonlySet<string> {
  const keys = new Set<string>();
  for (const rawField of snapshotFields(formSnapshot)) {
    if (!rawField || typeof rawField !== "object") continue;
    const field = rawField as Record<string, unknown>;
    if (field.type === "file" && typeof field.key === "string") {
      keys.add(field.key);
    }
  }
  for (const field of currentFields) {
    if (field.type === "file") keys.add(field.key);
  }
  return keys;
}
