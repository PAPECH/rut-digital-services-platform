import type { FormField } from "@/entities/form/model/types";

export function FormFieldStatusControls({
  field,
  onChange,
}: {
  field: FormField;
  onChange: (field: FormField) => void;
}) {
  return (
    <div className="form-field-status-controls" aria-label="Состояние поля">
      <label className="form-field-status-control">
        <input
          type="checkbox"
          checked={field.required}
          onChange={(event) =>
            onChange({ ...field, required: event.target.checked })
          }
        />
        <span>
          <strong>Обязательное</strong>
          <small>Без ответа форму нельзя отправить</small>
        </span>
      </label>
      <label className="form-field-status-control">
        <input
          type="checkbox"
          checked={field.active}
          onChange={(event) =>
            onChange({ ...field, active: event.target.checked })
          }
        />
        <span>
          <strong>Активное</strong>
          <small>Поле показывается пользователю</small>
        </span>
      </label>
    </div>
  );
}
