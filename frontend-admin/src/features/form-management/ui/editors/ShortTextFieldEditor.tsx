import type {
  FormFieldEditorProps,
  ShortTextField,
} from "@/entities/form/model/types";
import { EditorField, nullable } from "./EditorFields";
export function ShortTextFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<ShortTextField>) {
  const set = (patch: Partial<ShortTextField>) =>
    onChange({ ...field, ...patch });
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
      <EditorField label="Мин. длина">
        <input
          className="input"
          type="number"
          min={0}
          value={field.min_length}
          onChange={(e) => set({ min_length: Number(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Макс. длина">
        <input
          className="input"
          type="number"
          min={1}
          value={field.max_length}
          onChange={(e) => set({ max_length: Number(e.target.value) })}
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
