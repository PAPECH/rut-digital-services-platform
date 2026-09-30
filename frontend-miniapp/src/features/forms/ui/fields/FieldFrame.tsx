import type { ReactNode } from "react";
import type { FormField } from "@/entities/form/model/types";
export function FieldFrame({
  field,
  children,
}: {
  field: FormField;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="field-label">
        {field.label}
        {field.required ? (
          <span style={{ color: "var(--st-rej-fg)" }}> *</span>
        ) : null}
      </label>
      {children}
      {field.help_text ? (
        <div style={{ marginTop: 5, fontSize: 12, color: "var(--ink-400)" }}>
          {field.help_text}
        </div>
      ) : null}
    </div>
  );
}
