import type { FieldInputProps, SelectField } from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function SelectFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<SelectField>) {
  return (
    <FieldFrame field={field}>
      <select
        className="select"
        disabled={disabled}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Выберите…</option>
        {field.options.map((option) => (
          <option value={option.value} key={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldFrame>
  );
}
