import type { FormField } from "@/entities/form/model/types";
import { Icon } from "@/components/Icon";

function attachmentCount(value: unknown): number {
  if (!Array.isArray(value)) return 0;
  return value.filter(
    (item) => typeof item === "number" && Number.isInteger(item) && item > 0,
  ).length;
}

function fileCountLabel(count: number): string {
  const remainder100 = count % 100;
  const remainder10 = count % 10;
  if (remainder100 >= 11 && remainder100 <= 14) return `${count} файлов`;
  if (remainder10 === 1) return `${count} файл`;
  if (remainder10 >= 2 && remainder10 <= 4) return `${count} файла`;
  return `${count} файлов`;
}

// Resolves a stored `radio`/`select`/`multiselect` option value to its option's label; falls
// back to the raw value for every other field type and for a value that no longer matches any
// currently defined option (e.g. an option renamed/removed after older submissions were made).
function resolveOptionLabel(field: FormField, rawValue: string): string {
  if (field.type === "select" || field.type === "radio" || field.type === "multiselect") {
    const match = field.options.find((option) => option.value === rawValue);
    if (match) return match.label;
  }
  return rawValue;
}

export function SubmissionTableFieldValue({
  field,
  value,
  onOpen,
}: {
  field: FormField;
  value: unknown;
  onOpen: () => void;
}) {
  if (field.type === "file") {
    const count = attachmentCount(value);
    if (!count) return <span className="muted">Нет файлов</span>;
    return (
      <button
        className="submission-table-file-count"
        type="button"
        onClick={onOpen}
        aria-label={`${fileCountLabel(count)}. Открыть заявку`}
      >
        <span className="ico"><Icon.Paperclip /></span>
        {fileCountLabel(count)}
      </button>
    );
  }
  if (value === null || value === undefined || value === "") {
    return <span className="muted">—</span>;
  }
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (Array.isArray(value)) return value.map((item) => resolveOptionLabel(field, String(item))).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return resolveOptionLabel(field, String(value));
}
