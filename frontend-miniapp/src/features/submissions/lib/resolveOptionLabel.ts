interface SnapshotOption {
  value: string;
  label: string;
}

function isSnapshotOption(value: unknown): value is SnapshotOption {
  return (
    !!value &&
    typeof value === "object" &&
    typeof (value as Record<string, unknown>).value === "string" &&
    typeof (value as Record<string, unknown>).label === "string"
  );
}

// `form_snapshot` is the frozen field schema (including each choice field's options) taken from
// the published form version a submission was made against -- reading it here (rather than the
// form's current, possibly-since-edited schema) keeps a submission readable exactly as it was
// answered, even if the live form's options have since changed or been removed.
function readSnapshotOptions(
  formSnapshot: Record<string, unknown>,
  fieldKey: string,
): SnapshotOption[] | null {
  const fields = Array.isArray(formSnapshot.fields) ? formSnapshot.fields : [];
  for (const rawField of fields) {
    if (!rawField || typeof rawField !== "object") continue;
    const field = rawField as Record<string, unknown>;
    if (field.key !== fieldKey) continue;
    return Array.isArray(field.options) ? field.options.filter(isSnapshotOption) : null;
  }
  return null;
}

/** Resolves one stored `radio`/`select` value to its option's label; falls back to the raw value
 * when the field isn't a choice field or the value no longer matches any known option. */
export function resolveOptionLabel(
  formSnapshot: Record<string, unknown>,
  fieldKey: string,
  rawValue: string,
): string {
  const options = readSnapshotOptions(formSnapshot, fieldKey);
  return options?.find((option) => option.value === rawValue)?.label ?? rawValue;
}

/** Resolves a stored `multiselect` array to a comma-separated list of option labels, in the
 * stored order, each falling back to its raw value individually when unresolved. */
export function resolveOptionLabels(
  formSnapshot: Record<string, unknown>,
  fieldKey: string,
  rawValues: unknown[],
): string {
  return rawValues.map((value) => resolveOptionLabel(formSnapshot, fieldKey, String(value))).join(", ");
}
