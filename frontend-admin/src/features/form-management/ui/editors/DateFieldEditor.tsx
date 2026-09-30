import type {
  DateField,
  FormFieldEditorProps,
} from "@/entities/form/model/types";
import { EditorField, nullable } from "./EditorFields";
export function DateFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<DateField>) {
  const set = (patch: Partial<DateField>) => onChange({ ...field, ...patch });
  return (
    <div className="content-editor-grid">
      <EditorField label="По умолчанию">
        <input
          className="input"
          type="date"
          value={field.default ?? ""}
          onChange={(e) => set({ default: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Минимальная дата">
        <input
          className="input"
          type="date"
          value={field.min ?? ""}
          onChange={(e) => set({ min: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Максимальная дата">
        <input
          className="input"
          type="date"
          value={field.max ?? ""}
          onChange={(e) => set({ max: nullable(e.target.value) })}
        />
      </EditorField>
    </div>
  );
}
