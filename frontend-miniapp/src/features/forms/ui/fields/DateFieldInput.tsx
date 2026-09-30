import type { DateField, FieldInputProps } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function DateFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<DateField>) {
  return (
    <FieldFrame field={field}>
      <input
        className="input"
        type="date"
        disabled={disabled}
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </FieldFrame>
  );
}
