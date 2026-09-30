import type {
  FormFieldEditorProps,
  MultiselectField,
} from "@/entities/form/model/types";
import { EditorField, nullableNumber } from "./EditorFields";
import { OptionsEditor } from "./OptionsEditor";
export function MultiselectFieldEditor({
  field,
  onChange,
}: FormFieldEditorProps<MultiselectField>) {
  const defaultValues = field.default ?? [];
  return (
    <>
      <OptionsEditor
        options={field.options}
        onChange={(options) => {
          const values = new Set(options.map((o) => o.value));
          const nextDefault = field.default
            ? field.default.filter((value) => values.has(value))
            : null;
          onChange({
            ...field,
            options,
            default: nextDefault && nextDefault.length ? nextDefault : null,
          });
        }}
      />
      <EditorField label="По умолчанию отмечены">
        <div className="content-nested-list">
          {field.options.map((o) => (
            <label
              className="content-checkbox"
              key={o.value}
              style={{ display: "flex", gap: 8, alignItems: "center" }}
            >
              <input
                type="checkbox"
                checked={defaultValues.includes(o.value)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...defaultValues, o.value]
                    : defaultValues.filter((value) => value !== o.value);
                  onChange({ ...field, default: next.length ? next : null });
                }}
              />
              {o.label}
            </label>
          ))}
        </div>
      </EditorField>
      <div className="content-editor-grid">
        <EditorField label="Минимум выбрано">
          <input
            className="input"
            type="number"
            min={0}
            max={field.options.length}
            value={field.min_selected ?? ""}
            onChange={(e) =>
              onChange({
                ...field,
                min_selected: nullableNumber(e.target.value),
              })
            }
          />
        </EditorField>
        <EditorField label="Максимум выбрано">
          <input
            className="input"
            type="number"
            min={0}
            max={field.options.length}
            value={field.max_selected ?? ""}
            onChange={(e) =>
              onChange({
                ...field,
                max_selected: nullableNumber(e.target.value),
              })
            }
          />
        </EditorField>
      </div>
    </>
  );
}
