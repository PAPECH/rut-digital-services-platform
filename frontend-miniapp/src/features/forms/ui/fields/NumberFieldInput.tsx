import type { FieldInputProps, NumberField } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function NumberFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<NumberField>) {
  return (
    <FieldFrame field={field}>
      <input
        className="input"
        type="number"
        inputMode="decimal"
        disabled={disabled}
        placeholder={field.placeholder ?? ""}
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        step={field.step}
        value={value === "" ? "" : Number(value)}
        onChange={(e) =>
          onChange(e.target.value === "" ? "" : Number(e.target.value))
        }
      />
    </FieldFrame>
  );
}
