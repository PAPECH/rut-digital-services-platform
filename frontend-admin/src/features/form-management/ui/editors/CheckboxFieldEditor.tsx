import type {
  CheckboxField,
  FormFieldEditorProps,
} from "@/entities/form/model/types";
export function CheckboxFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<CheckboxField>) {
  return (
    <label className="content-checkbox">
      <input
        type="checkbox"
        checked={field.default}
        onChange={(e) => onChange({ ...field, default: e.target.checked })}
      />
      Отмечено по умолчанию
    </label>
  );
}
