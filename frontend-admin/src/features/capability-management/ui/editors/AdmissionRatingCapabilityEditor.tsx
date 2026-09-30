import { useEffect, useState } from "react";

import {
  defaultAdmissionRatingConfig,
  type AdmissionRatingConfig,
  type CapabilityEditorProps,
} from "@/entities/capability/model/types";

function configFrom(value: Record<string, unknown>): AdmissionRatingConfig {
  return { ...defaultAdmissionRatingConfig, ...value } as AdmissionRatingConfig;
}

export function AdmissionRatingCapabilityEditor({
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
  const dirty = JSON.stringify(draft) !== JSON.stringify(configFrom(installation.config));
  // An installation that has never been saved (config_revision === 0) must be savable with
  // unedited default values -- otherwise there is no way to reach Enable at all, since Enable
  // requires a saved config. Only a *previously configured* installation needs an actual edit
  // before Save does anything.
  const canSave = dirty || installation.config_revision === 0;
  const patch = <Key extends keyof AdmissionRatingConfig>(
    key: Key,
    value: AdmissionRatingConfig[Key],
  ) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="capability-editor">
      <div className="capability-config-grid">
        <label>
          Год приёма
          <input className="input" type="number" value={draft.admission_year}
            onChange={(event) => patch("admission_year", Number(event.target.value))} />
        </label>
        <label>
          Интервал обновления, сек.
          <input className="input" type="number" min={300} max={86400}
            value={draft.polling_interval_seconds}
            onChange={(event) => patch("polling_interval_seconds", Number(event.target.value))} />
        </label>
        <label className="content-checkbox capability-checkbox">
          <input type="checkbox" checked={draft.notifications_enabled}
            onChange={(event) => patch("notifications_enabled", event.target.checked)} />
          Уведомлять об изменениях
        </label>
        <label className="capability-config-wide">
          Заголовок
          <input className="input" value={draft.title}
            onChange={(event) => patch("title", event.target.value)} />
        </label>
        <label className="capability-config-wide">
          Подзаголовок
          <textarea className="textarea" rows={2} value={draft.subtitle}
            onChange={(event) => patch("subtitle", event.target.value)} />
        </label>
        <label>
          Подпись поля
          <input className="input" value={draft.lookup_label}
            onChange={(event) => patch("lookup_label", event.target.value)} />
        </label>
        <label>
          Текст «не найдено»
          <input className="input" value={draft.not_found_text}
            onChange={(event) => patch("not_found_text", event.target.value)} />
        </label>
      </div>
      <div className="capability-actions">
        <button type="button" className="btn btn-primary" disabled={!canSave || busy !== null}
          onClick={() => void onSave({ ...draft })}>
          {busy?.endsWith(":save") ? "Сохранение…" : "Сохранить настройки"}
        </button>
        <button type="button" className="btn btn-secondary"
          disabled={dirty || !installation.config_revision || busy !== null}
          onClick={() => void onTest()}>
          {busy?.endsWith(":test") ? "Проверка…" : "Проверить подключение"}
        </button>
      </div>
    </div>
  );
}
