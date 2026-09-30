import type {
  FormFieldEditorProps,
  NumberField,
} from "@/entities/form/model/types";
import { EditorField, nullable, nullableNumber } from "./EditorFields";
export function NumberFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<NumberField>) {
  const set = (patch: Partial<NumberField>) => onChange({ ...field, ...patch });
  return (
    <div className="content-editor-grid">
      <EditorField label="Placeholder">
        <input
          className="input"
          value={field.placeholder ?? ""}
          onChange={(e) => set({ placeholder: nullable(e.target.value) })}
        />
      </EditorField>
      <EditorField label="По умолчанию">
        <input
          className="input"
          type="number"
          value={field.default ?? ""}
          onChange={(e) => set({ default: nullableNumber(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Минимум">
        <input
          className="input"
          type="number"
          value={field.min ?? ""}
          onChange={(e) => set({ min: nullableNumber(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Максимум">
        <input
          className="input"
          type="number"
          value={field.max ?? ""}
          onChange={(e) => set({ max: nullableNumber(e.target.value) })}
        />
      </EditorField>
      <EditorField label="Шаг">
        <input
          className="input"
          type="number"
          min="0.000001"
          value={field.step}
          onChange={(e) => set({ step: Number(e.target.value) })}
        />
      </EditorField>
    </div>
  );
}
