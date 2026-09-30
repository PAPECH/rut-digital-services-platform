import type { BotSettings, ProfileFieldDefinition } from "@/api/types";
import {
  availableProfileDisplayFields,
  DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS,
} from "@/entities/profile/model/profileDisplayFields";

export function SubmissionTableFieldsEditor({
  settings,
  profileSchema,
  onChange,
}: {
  settings: BotSettings;
  profileSchema: ProfileFieldDefinition[];
  onChange: (settings: BotSettings) => void;
}) {
  const fields = availableProfileDisplayFields(profileSchema);
  const selectedKeys =
    settings.submission_table?.profile_fields ??
    [...DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS];
  const selected = new Set(selectedKeys);

  const toggle = (key: string) => {
    const nextSelected = new Set(selected);
    if (nextSelected.has(key)) nextSelected.delete(key);
    else nextSelected.add(key);
    onChange({
      ...settings,
      submission_table: {
        profile_fields: fields
          .filter((field) => nextSelected.has(field.key))
          .map((field) => field.key),
      },
    });
  };

  return (
    <section className="submission-table-settings">
      <div>
        <span className="field-label">Данные пользователя в таблице заявок</span>
        <p className="profile-schema-editor__hint">
          Выберите профильные поля, которые администратор увидит отдельными
          столбцами. Настройка действует только для выбранного бота.
        </p>
      </div>
      <div className="submission-table-settings__grid">
        {fields.map((field) => (
          <label className="submission-table-settings__option" key={field.key}>
            <input
              type="checkbox"
              checked={selected.has(field.key)}
              onChange={() => toggle(field.key)}
            />
            <span>
              <strong>{field.label}</strong>
              <small>
                {field.source === "platform" ? "Основное поле" : "Поле бота"}
              </small>
            </span>
          </label>
        ))}
      </div>
      {!profileSchema.length ? (
        <p className="muted">
          Дополнительные поля появятся здесь после добавления в настройках бота.
        </p>
      ) : null}
    </section>
  );
}
