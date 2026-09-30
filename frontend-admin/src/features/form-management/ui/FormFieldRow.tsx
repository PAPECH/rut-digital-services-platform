import { useState } from "react";

import type { FormField, FormFieldType } from "@/entities/form/model/types";
import { convertFormFieldType } from "@/features/form-management/lib/fieldFactory";
import { FORM_FIELD_TYPES } from "@/features/form-management/model/fieldTypes";
import { FormFieldAdvancedEditor } from "@/features/form-management/ui/FormFieldAdvancedEditor";
import { FormFieldStatusControls } from "@/features/form-management/ui/FormFieldStatusControls";
import { EditorField } from "@/features/form-management/ui/editors/EditorFields";

export function FormFieldRow({
  field,
  index,
  isFirst,
  isLast,
  onChange,
  onMove,
  onDelete,
}: {
  field: FormField;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  onChange: (field: FormField) => void;
  onMove: (direction: -1 | 1) => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = FORM_FIELD_TYPES.find((type) => type.value === field.type)?.label;
  return (
    <section className={`form-field-row${field.active ? "" : " form-field-row--inactive"}`}>
      <header className="form-field-row__header">
        <div className="form-field-row__identity">
          <span className="form-field-row__number">{index + 1}</span>
          <span>
            <strong>{field.label.trim() || `Поле ${index + 1}`}</strong>
            <small>{typeLabel ?? field.type}</small>
          </span>
        </div>
        <div className="form-field-row__actions">
          <button className="btn btn-ghost btn-sm" type="button" disabled={isFirst} onClick={() => onMove(-1)} aria-label="Поднять поле">↑</button>
          <button className="btn btn-ghost btn-sm" type="button" disabled={isLast} onClick={() => onMove(1)} aria-label="Опустить поле">↓</button>
          <button className="btn btn-secondary btn-sm" type="button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Свернуть" : "Настроить"}
          </button>
          <button className="btn btn-danger btn-sm" type="button" onClick={onDelete}>Удалить</button>
        </div>
      </header>
      <div className="form-field-row__settings">
        <EditorField label="Название поля">
          <input
            aria-label={`Название поля ${index + 1}`}
            className="input"
            value={field.label}
            onChange={(event) => onChange({ ...field, label: event.target.value })}
          />
        </EditorField>
        <EditorField label="Тип ответа">
          <select
            aria-label={`Тип поля ${index + 1}`}
            className="select"
            value={field.type}
            onChange={(event) =>
              onChange(convertFormFieldType(field, event.target.value as FormFieldType))
            }
          >
            {FORM_FIELD_TYPES.map((type) => (
              <option value={type.value} key={type.value}>{type.label}</option>
            ))}
          </select>
        </EditorField>
        <FormFieldStatusControls field={field} onChange={onChange} />
      </div>
      {expanded ? <FormFieldAdvancedEditor field={field} onChange={onChange} /> : null}
    </section>
  );
}
