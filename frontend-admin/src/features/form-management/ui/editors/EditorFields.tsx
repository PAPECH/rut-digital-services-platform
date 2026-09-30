import type { ReactNode } from "react";

export function EditorField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="content-editor-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export const nullable = (value: string): string | null =>
  value.trim() ? value : null;
export const nullableNumber = (value: string): number | null =>
  value === "" ? null : Number(value);
