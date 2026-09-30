import type { FormDraft, FormField, FormFieldType } from "@/entities/form/model/types";
import { createFormField } from "@/features/form-management/lib/fieldFactory";
import { FORM_FIELD_TYPES } from "@/features/form-management/model/fieldTypes";
import { FormFieldRow } from "@/features/form-management/ui/FormFieldRow";
import { FormMetadataEditor } from "@/features/form-management/ui/FormMetadataEditor";

export function FormDraftEditor({
  draft,
  onChange,
}: {
  draft: FormDraft;
  onChange: (draft: FormDraft) => void;
}) {
  const fields = draft.fields;
  const replace = (index: number, field: FormField) =>
    onChange({
      ...draft,
      fields: fields.map((item, current) => current === index ? field : item),
    });
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= fields.length) return;
    const next = [...fields];
    [next[index], next[target]] = [next[target], next[index]];
    onChange({ ...draft, fields: next });
  };

  return (
    <div className="form-builder-editor">
      <FormMetadataEditor draft={draft} onChange={onChange} />
      <div className="form-builder-fields-head">
        <div>
          <h3>Поля ({fields.length})</h3>
          <span>До 100 полей в одной форме</span>
        </div>
        <select
          className="select"
          value=""
          disabled={fields.length >= 100}
          onChange={(event) => {
            if (!event.target.value) return;
            onChange({
              ...draft,
              fields: [...fields, createFormField(event.target.value as FormFieldType)],
            });
          }}
        >
          <option value="">Добавить поле…</option>
          {FORM_FIELD_TYPES.map((type) => (
            <option value={type.value} key={type.value}>{type.label}</option>
          ))}
        </select>
      </div>
      {fields.length ? (
        <div className="form-field-list">
          {fields.map((field, index) => (
            <FormFieldRow
              key={field.key}
              field={field}
              index={index}
              isFirst={index === 0}
              isLast={index === fields.length - 1}
              onChange={(updated) => replace(index, updated)}
              onMove={(direction) => move(index, direction)}
              onDelete={() => onChange({
                ...draft,
                fields: fields.filter((_, current) => current !== index),
              })}
            />
          ))}
        </div>
      ) : (
        <div className="content-empty-state">
          <strong>Пока нет полей</strong>
          <span>Выберите тип в меню «Добавить поле».</span>
        </div>
      )}
    </div>
  );
}
