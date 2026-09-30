import { useEffect, useState } from "react";

import {
  defaultRutScheduleConfig,
  type CapabilityEditorProps,
  type RutScheduleConfig,
} from "@/entities/capability/model/types";

function configFrom(value: Record<string, unknown>): RutScheduleConfig {
  return { ...defaultRutScheduleConfig, ...value } as RutScheduleConfig;
}

export function RutScheduleCapabilityEditor({
  installation,
  busy,
  onSave,
}: CapabilityEditorProps) {
  const [draft, setDraft] = useState(() => configFrom(installation.config));
  useEffect(
    () => setDraft(configFrom(installation.config)),
    [installation.config, installation.config_revision],
  );
  const dirty = JSON.stringify(draft) !== JSON.stringify(configFrom(installation.config));
  // An installation that has never been saved (config_revision === 0) must be savable with
  // unedited default values -- otherwise there is no way to reach Enable at all.
  const canSave = dirty || installation.config_revision === 0;
  const patch = <Key extends keyof RutScheduleConfig>(
    key: Key,
    value: RutScheduleConfig[Key],
  ) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="capability-editor">
      <div className="capability-config-grid">
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
          Кэш расписания группы, сек.
          <input
            className="input"
            type="number"
            min={60}
            max={86400}
            value={draft.group_cache_ttl_seconds}
            onChange={(event) => patch("group_cache_ttl_seconds", Number(event.target.value))}
          />
        </label>
        <label>
          Интервал синхронизации справочника, сек.
          <input
            className="input"
            type="number"
            min={300}
            max={604800}
            value={draft.hierarchy_sync_interval_seconds}
            onChange={(event) =>
              patch("hierarchy_sync_interval_seconds", Number(event.target.value))
            }
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
      </div>
    </div>
  );
}
