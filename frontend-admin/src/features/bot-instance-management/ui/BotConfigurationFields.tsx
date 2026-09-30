import type { ProfileFieldDefinition } from "@/api/types";
import {
  coreProfileFields,
  coreProfileKeys,
} from "@/entities/profile/model/profileFields";

const EMPTY_FIELD: ProfileFieldDefinition = {
  key: "",
  label: "",
  type: "string",
  required: false,
  shared: false,
};

export function BotConfigurationFields({
  branding,
  fields,
  onBrandingChange,
  onFieldsChange,
}: {
  branding: Record<string, unknown>;
  fields: ProfileFieldDefinition[];
  onBrandingChange: (value: Record<string, unknown>) => void;
  onFieldsChange: (value: ProfileFieldDefinition[]) => void;
}) {
  const customFields = fields.filter((field) => !coreProfileKeys.has(field.key));
  const setField = (
    index: number,
    patch: Partial<ProfileFieldDefinition>,
  ) =>
    onFieldsChange(
      customFields.map((field, current) =>
        current === index ? { ...field, ...patch } : field,
      ),
    );

  return (
    <>
      <div className="settings-form__wide bot-branding-fields">
        <label>
          <span className="field-label">Основной цвет</span>
          <input
            className="input"
            type="color"
            value={String(branding.primary_color || "#335eea")}
            onChange={(event) =>
              onBrandingChange({
                ...branding,
                primary_color: event.target.value,
              })
            }
          />
        </label>
        <label>
          <span className="field-label">URL логотипа</span>
          <input
            className="input"
            value={String(branding.logo_url || "")}
            placeholder="https://… или /logo.png"
            onChange={(event) =>
              onBrandingChange({ ...branding, logo_url: event.target.value || null })
            }
          />
        </label>
      </div>

      <div className="settings-form__wide profile-schema-editor">
        <div className="profile-schema-editor__head">
          <div>
            <span className="field-label">Дополнительные поля профиля</span>
            <p className="profile-schema-editor__hint">
              Обязательные для всех: {coreProfileFields.join(", ")}.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onFieldsChange([...customFields, { ...EMPTY_FIELD }])}
          >
            Добавить поле
          </button>
        </div>
        {customFields.map((field, index) => (
          <div className="profile-schema-row" key={index}>
            <input
              className="input"
              value={field.key}
              placeholder="job_title"
              onChange={(event) =>
                setField(index, {
                  key: event.target.value.toLowerCase().replace(/[^a-z0-9_.-]/g, "_"),
                })
              }
            />
            <input
              className="input"
              value={field.label}
              placeholder="Название поля"
              onChange={(event) => setField(index, { label: event.target.value })}
            />
            <select
              className="select"
              value={field.type}
              onChange={(event) =>
                setField(index, {
                  type: event.target.value as ProfileFieldDefinition["type"],
                })
              }
            >
              <option value="string">Текст</option>
              <option value="email">Email</option>
              <option value="phone">Телефон</option>
              <option value="boolean">Да/нет</option>
              <option value="date">Дата</option>
              <option value="number">Число</option>
              <option value="select">Список</option>
            </select>
            {field.type === "select" ? (
              <input
                className="input profile-schema-options"
                value={(field.options ?? []).join(", ")}
                placeholder="Вариант 1, Вариант 2"
                onChange={(event) =>
                  setField(index, {
                    options: event.target.value
                      .split(",")
                      .map((option) => option.trim())
                      .filter(Boolean),
                  })
                }
              />
            ) : null}
            <label className="staff-permission">
              <input
                type="checkbox"
                checked={field.required}
                onChange={(event) => setField(index, { required: event.target.checked })}
              />
              Обязательно
            </label>
            <button
              className="btn btn-danger btn-sm"
              type="button"
              onClick={() => onFieldsChange(customFields.filter((_, current) => current !== index))}
            >
              Удалить
            </button>
          </div>
        ))}
        {!customFields.length ? (
          <span className="muted">Дополнительных полей пока нет.</span>
        ) : null}
      </div>
    </>
  );
}
