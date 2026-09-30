import type {
  CheckboxField,
  FieldInputProps,
} from "@/entities/form/model/types";
export function CheckboxFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<CheckboxField>) {
  return (
    <div>
      <label
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
          cursor: disabled ? "default" : "pointer",
        }}
      >
        <input
          type="checkbox"
          disabled={disabled}
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span style={{ fontSize: 14 }}>
          {field.label}
          {field.required ? (
            <span style={{ color: "var(--st-rej-fg)" }}> *</span>
          ) : null}
        </span>
      </label>
      {field.help_text ? (
        <div
          style={{
            margin: "5px 0 0 26px",
            fontSize: 12,
            color: "var(--ink-400)",
          }}
        >
          {field.help_text}
        </div>
      ) : null}
    </div>
  );
}
