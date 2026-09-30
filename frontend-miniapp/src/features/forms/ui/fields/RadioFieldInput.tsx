import type { FieldInputProps, RadioField } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function RadioFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<RadioField>) {
  return (
    <FieldFrame field={field}>
      <div style={{ display: "grid", gap: 8 }}>
        {field.options.map((option) => (
          <label
            key={option.value}
            style={{ display: "flex", gap: 9, alignItems: "center" }}
          >
            <input
              type="radio"
              name={field.key}
              disabled={disabled}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </FieldFrame>
  );
}
