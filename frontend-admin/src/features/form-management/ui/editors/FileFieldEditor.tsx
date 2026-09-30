import type {
  FileField,
  FormFieldEditorProps,
} from "@/entities/form/model/types";
import { EditorField } from "./EditorFields";
export function FileFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<FileField>) {
  return (
    <div className="content-editor-grid">
      <EditorField label="MIME-типы через запятую">
        <input
          className="input"
          placeholder="application/pdf,image/png"
          value={field.accepted_mime_types.join(",")}
          onChange={(e) =>
            onChange({
              ...field,
              accepted_mime_types: e.target.value
                .split(",")
                .map((v) => v.trim())
                .filter(Boolean),
            })
          }
        />
      </EditorField>
      <EditorField label="Максимум файлов">
        <input
          className="input"
          type="number"
          min={1}
          max={10}
          value={field.max_files}
          onChange={(e) =>
            onChange({ ...field, max_files: Number(e.target.value) })
          }
        />
      </EditorField>
      <EditorField label="Макс. размер, МБ">
        <input
          className="input"
          type="number"
          min={1}
          max={20}
          value={Math.round(field.max_size_bytes / 1024 / 1024)}
          onChange={(e) =>
            onChange({
              ...field,
              max_size_bytes: Number(e.target.value) * 1024 * 1024,
            })
          }
        />
      </EditorField>
    </div>
  );
}
