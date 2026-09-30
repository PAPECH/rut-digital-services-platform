import type {
  FieldInputProps,
  LongTextField,
} from "@/entities/form/model/types";
import { FieldFrame } from "./FieldFrame";
export function LongTextFieldInput({
  field,
  value,
  onChange,
  disabled,
}: FieldInputProps<LongTextField>) {
  return (
    <FieldFrame field={field}>
      <textarea
        className="textarea"
        disabled={disabled}
        placeholder={field.placeholder ?? ""}
        minLength={field.min_length}
        maxLength={field.max_length}
  
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </FieldFrame>
  );
}
