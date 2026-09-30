import type {
  FormFieldEditorProps,
  PhoneField,
} from "@/entities/form/model/types";
import { EditorField, nullable } from "./EditorFields";
export function PhoneFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<PhoneField>) {
  const set = (patch: Partial<PhoneField>) => onChange({ ...field, ...patch });
  return (
    <div className="content-editor-grid">
      <EditorField label="Placeholder">
        <input
          className="input"
          value={field.placeholder ?? ""}
          onChange={(e) => set({ placeholder: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Значение по умолчанию">
        <input
          className="input"
          value={field.default ?? ""}
          onChange={(e) => set({ default: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Регулярное выражение">
        <input
          className="input"
          value={field.pattern ?? ""}
          onChange={(e) => set({ pattern: nullable(e.target.value) })}
        />
      </EditorField>
    </div>
  );
}
