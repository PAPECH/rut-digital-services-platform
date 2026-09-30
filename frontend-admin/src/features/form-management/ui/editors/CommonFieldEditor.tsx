import type {
  FormField,
  FormFieldEditorProps,
} from "@/entities/form/model/types";
import { EditorField, nullable } from "./EditorFields";

export function CommonFieldEditor({ field, onChange }: FormFieldEditorProps) {
  const change = (patch: Partial<FormField>) =>
    onChange({ ...field, ...patch } as FormField);
  return (
    <div className="content-editor-grid">
      <EditorField label="Название">
        <input
          className="input"
          value={field.label}
          onChange={(event) => change({ label: event.target.value })}
        />
      </EditorField>
      <EditorField label="Стабильный ключ">
        <input
          className="input"
          value={field.key}
          onChange={(event) => change({ key: event.target.value })}
        />
      </EditorField>
      <EditorField label="Подсказка">
        <input
          className="input"
          value={field.help_text ?? ""}
          onChange={(event) =>
            change({ help_text: nullable(event.target.value) })
          }
        />
      </EditorField>
      <EditorField label="Поле профиля">
        <input
          className="input"
          placeholder="например, email"
          value={field.profile_key ?? ""}
          onChange={(event) =>
            change({ profile_key: nullable(event.target.value) })
          }
        />
      </EditorField>
      <label className="content-checkbox">
        <input
          type="checkbox"
          checked={field.required}
          onChange={(event) => change({ required: event.target.checked })}
        />
        Обязательное
      </label>
      <label className="content-checkbox">
        <input
          type="checkbox"
          checked={field.active}
          onChange={(event) => change({ active: event.target.checked })}
        />
        Активное
      </label>
    </div>
  );
}
