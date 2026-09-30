import type {
  FieldInputProps,
  MultiselectField,
} from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function MultiselectFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<MultiselectField>) {
  const selected = Array.isArray(value) ? (value as string[]) : [];
  const toggle = (optionValue: string, checked: boolean) => {
    if (checked) {
      if (selected.includes(optionValue)) return;
      onChange([...selected, optionValue]);
    } else {
      onChange(selected.filter((item) => item !== optionValue));
    }
  };
  return (
    <FieldFrame field={field}>
      <div style={{ display: "grid", gap: 8 }}>
        {field.options.map((option) => (
          <label
            key={option.value}
            style={{ display: "flex", gap: 9, alignItems: "center" }}
          >
            <input
              type="checkbox"
              disabled={disabled}
              checked={selected.includes(option.value)}
              onChange={(e) => toggle(option.value, e.target.checked)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </FieldFrame>
  );
}
