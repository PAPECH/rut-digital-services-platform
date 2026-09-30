import type { EmailField, FieldInputProps } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function EmailFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<EmailField>) {
  return (
    <FieldFrame field={field}>
      <input
        className="input"
        type="email"
        inputMode="email"
        autoComplete="email"
        disabled={disabled}
        placeholder={field.placeholder ?? ""}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </FieldFrame>
  );
}
