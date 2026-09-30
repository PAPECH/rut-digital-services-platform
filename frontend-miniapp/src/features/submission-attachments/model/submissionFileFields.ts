export function submissionFileFieldKeys(
  formSnapshot: Record<string, unknown>,
): ReadonlySet<string> {
  const keys = new Set<string>();
  const fields = Array.isArray(formSnapshot.fields) ? formSnapshot.fields : [];
  for (const rawField of fields) {
    if (!rawField || typeof rawField !== "object") continue;
    const field = rawField as Record<string, unknown>;
    if (field.type === "file" && typeof field.key === "string") {
      keys.add(field.key);
    }
  }
  return keys;
}
