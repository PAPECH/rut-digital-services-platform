import { useEffect, useState } from "react";

import {
  defaultRequestStatusConfig,
  type CapabilityEditorProps,
  type RequestStatusConfig,
} from "@/entities/capability/model/types";

function configFrom(value: Record<string, unknown>): RequestStatusConfig {
  return { ...defaultRequestStatusConfig, ...value } as RequestStatusConfig;
}

export function RequestStatusCapabilityEditor({
  installation,
  busy,
  onSave,
  onTest,
}: CapabilityEditorProps) {
  const [draft, setDraft] = useState(() => configFrom(installation.config));
  useEffect(
    () => setDraft(configFrom(installation.config)),
    [installation.config, installation.config_revision],
  );
  const dirty =
    JSON.stringify(draft) !== JSON.stringify(configFrom(installation.config));
  // An installation that has never been saved (config_revision === 0) must be savable with
  // unedited default values -- otherwise there is no way to reach Enable at all, since Enable
  // requires a saved config. Only a *previously configured* installation needs an actual edit
  // before Save does anything.
  const canSave = dirty || installation.config_revision === 0;
  const patch = <Key extends keyof RequestStatusConfig>(
    key: Key,
    value: RequestStatusConfig[Key],
  ) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="capability-editor">
      <div className="capability-config-grid">
        <label>
          Источник учётных данных
          <select
            className="select"
            value={draft.credential_ref}
            onChange={(event) =>
              patch(
                "credential_ref",
                event.target.value as RequestStatusConfig["credential_ref"],
              )
            }
          >
            <option value="legacy_google_sheets">
              Google Sheets платформы
            </option>
            <option value="mock">Тестовый файл</option>
          </select>
        </label>
        <label>
          ID таблицы
          <input
            className="input"
            value={draft.spreadsheet_id}
            onChange={(event) => patch("spreadsheet_id", event.target.value)}
          />
        </label>
        <label>
          Диапазон
          <input
            className="input"
            value={draft.sheet_range}
            onChange={(event) => patch("sheet_range", event.target.value)}
          />
        </label>
        <label>
          Интервал опроса, сек.
          <input
            className="input"
            type="number"
            min={60}
            max={86400}
            value={draft.polling_interval_seconds}
            onChange={(event) =>
              patch("polling_interval_seconds", Number(event.target.value))
            }
          />
        </label>
        <label>
          Колонка номера (с нуля)
          <input
            className="input"
            type="number"
            min={0}
            max={50}
            value={draft.request_number_column}
            onChange={(event) =>
              patch("request_number_column", Number(event.target.value))
            }
          />
        </label>
        <label>
          Колонка статуса (с нуля)
          <input
            className="input"
            type="number"
            min={0}
            max={50}
            value={draft.status_column}
            onChange={(event) =>
              patch("status_column", Number(event.target.value))
            }
          />
        </label>
        <label>
          Нормализация номера
          <select
            className="select"
            value={draft.normalization}
            onChange={(event) =>
              patch(
                "normalization",
                event.target.value as RequestStatusConfig["normalization"],
              )
            }
          >
            <option value="trim">Убрать пробелы по краям</option>
            <option value="compact">
              Убрать все пробелы и привести к верхнему регистру
            </option>
          </select>
        </label>
        <label className="content-checkbox capability-checkbox">
          <input
            type="checkbox"
            checked={draft.notifications_enabled}
            onChange={(event) =>
              patch("notifications_enabled", event.target.checked)
            }
          />
          Уведомлять об изменениях
        </label>
        <label className="capability-config-wide">
          Заголовок
          <input
            className="input"
            value={draft.title}
            onChange={(event) => patch("title", event.target.value)}
          />
        </label>
        <label className="capability-config-wide">
          Подзаголовок
          <textarea
            className="textarea"
            rows={2}
            value={draft.subtitle}
            onChange={(event) => patch("subtitle", event.target.value)}
          />
        </label>
        <label>
          Подпись поля
          <input
            className="input"
            value={draft.lookup_label}
            onChange={(event) => patch("lookup_label", event.target.value)}
          />
        </label>
        <label>
          Текст «не найдено»
          <input
            className="input"
            value={draft.not_found_text}
            onChange={(event) => patch("not_found_text", event.target.value)}
          />
        </label>
      </div>
      <div className="capability-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!canSave || busy !== null}
          onClick={() => void onSave({ ...draft })}
        >
          {busy?.endsWith(":save") ? "Сохранение…" : "Сохранить настройки"}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={dirty || !installation.config_revision || busy !== null}
          onClick={() => void onTest()}
        >
          {busy?.endsWith(":test") ? "Проверка…" : "Проверить подключение"}
        </button>
      </div>
    </div>
  );
}
