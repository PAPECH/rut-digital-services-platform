import type { FormField, FormFieldEditorProps } from "@/entities/form/model/types";
import { FORM_FIELD_TYPES } from "@/features/form-management/model/fieldTypes";
import { FormFieldEditorRegistry } from "@/features/form-management/ui/editors/FormFieldEditorRegistry";
import { EditorField, nullable } from "@/features/form-management/ui/editors/EditorFields";

export function FormFieldAdvancedEditor({
  field,
  onChange,
}: FormFieldEditorProps) {
  const change = (patch: Partial<FormField>) =>
    onChange({ ...field, ...patch } as FormField);
  const typeLabel = FORM_FIELD_TYPES.find((type) => type.value === field.type)?.label;
  return (
    <div className="form-field-advanced">
      <section className="form-field-advanced__section">
        <div className="form-field-advanced__heading">
          <strong>Общие настройки</strong>
          <span>Ключ, подсказка и связь с профилем</span>
        </div>
        <div className="content-editor-grid">
          <EditorField label="Стабильный ключ">
            <input
              className="input"
              value={field.key}
              onChange={(event) => change({ key: event.target.value })}
            />
          </EditorField>
          <EditorField label="Подсказка пользователю">
            <input
              className="input"
              value={field.help_text ?? ""}
              onChange={(event) => change({ help_text: nullable(event.target.value) })}
            />
          </EditorField>
          <EditorField label="Подставлять из поля профиля">
            <input
              className="input"
              placeholder="например, email"
              value={field.profile_key ?? ""}
              onChange={(event) => change({ profile_key: nullable(event.target.value) })}
            />
          </EditorField>
        </div>
      </section>
      <section className="form-field-advanced__section">
        <div className="form-field-advanced__heading">
          <strong>Настройки типа «{typeLabel ?? field.type}»</strong>
          <span>Ограничения и значение по умолчанию</span>
        </div>
        <FormFieldEditorRegistry field={field} onChange={onChange} />
      </section>
    </div>
  );
}
