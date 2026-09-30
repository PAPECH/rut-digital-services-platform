import type {
  FieldInputProps,
  ShortTextField,
} from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function ShortTextFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<ShortTextField>) {
  return (
    <FieldFrame field={field}>
      <input
        className="input"
        type="text"
        disabled={disabled}
        placeholder={field.placeholder ?? ""}
        minLength={field.min_length}
        maxLength={field.max_length}
        pattern={field.pattern ?? undefined}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </FieldFrame>
  );
}
