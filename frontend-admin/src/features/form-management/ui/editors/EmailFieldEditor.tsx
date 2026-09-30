import type {
  EmailField,
  FormFieldEditorProps,
} from "@/entities/form/model/types";
import { EditorField, nullable } from "./EditorFields";
export function EmailFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<EmailField>) {
  const set = (patch: Partial<EmailField>) => onChange({ ...field, ...patch });
  return (
    <div className="content-editor-grid">
      <EditorField label="Placeholder">
        <input
          className="input"
          type="email"
          value={field.placeholder ?? ""}
          onChange={(e) => set({ placeholder: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Значение по умолчанию">
        <input
          className="input"
          type="email"
          value={field.default ?? ""}
          onChange={(e) => set({ default: nullable(e.target.value) })}
        />
      </EditorField>
    </div>
  );
}
