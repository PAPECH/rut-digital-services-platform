import type { FieldInputProps, PhoneField } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function PhoneFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<PhoneField>) {
  return (
    <FieldFrame field={field}>
      <input
        className="input"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        disabled={disabled}
        placeholder={field.placeholder ?? ""}
        pattern={field.pattern ?? undefined}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </FieldFrame>
  );
}
