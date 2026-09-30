import type {
  FormFieldEditorProps,
  SelectField,
} from "@/entities/form/model/types";
import { EditorField } from "./EditorFields";
import { OptionsEditor } from "./OptionsEditor";
export function SelectFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<SelectField>) {
  return (
    <>
      <OptionsEditor
        options={field.options}
        onChange={(options) =>
          onChange({
            ...field,
            options,
            default: options.some((o) => o.value === field.default)
              ? field.default
              : null,
          })
        }
      />
      <EditorField label="По умолчанию">
        <select
          className="select"
          value={field.default ?? ""}
          onChange={(e) =>
            onChange({ ...field, default: e.target.value || null })
          }
        >
          <option value="">Не выбрано</option>
          {field.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </EditorField>
    </>
  );
}
