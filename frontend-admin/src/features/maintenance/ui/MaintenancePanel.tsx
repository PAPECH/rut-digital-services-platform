import { useEffect, useState } from "react";

import type { MaintenanceMode } from "@/api/types";
import {
  type MaintenanceDraft,
  useMaintenancePolicy,
} from "@/features/maintenance/model/useMaintenancePolicy";

const DEFAULT_DRAFT: MaintenanceDraft = {
  mode: "off",
  title: "Технические работы",
  message: "",
  retry_after_seconds: null,
  allow_admin: true,
};

export function MaintenancePanel({
  scope,
  title,
}: {
  scope: "current" | "global";
  title: string;
}) {
  const endpoint =
    scope === "global" ? "/maintenance/global" : "/maintenance/current";
  const { policy, loading, saving, error, save } =
    useMaintenancePolicy(endpoint);
  const [draft, setDraft] = useState<MaintenanceDraft>(DEFAULT_DRAFT);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!policy) return;
    setDraft({
      mode: policy.mode,
      title: policy.title,
      message: policy.message,
      retry_after_seconds: policy.retry_after_seconds,
      allow_admin: policy.allow_admin,
    });
  }, [policy]);

  return (
    <section className="card maintenance-panel">
      <div className="card-head">
        <div>
          <h2 className="card-title">{title}</h2>
          <p className="card-sub">
            Управляет плашкой и доступностью мини-приложения.
          </p>
        </div>
        <span className={`tag ${draft.mode === "off" ? "neutral" : "work"}`}>
          {draft.mode === "off" ? "Выключен" : "Включён"}
        </span>
      </div>
      <div className="card-body">
        {loading ? <p className="muted">Загрузка…</p> : null}
        {!loading ? (
          <div className="settings-form">
            <label>
              <span className="field-label">Режим</span>
              <select
                className="select"
                value={draft.mode}
                onChange={(event) => {
                  setSaved(false);
                  setDraft((current) => ({
                    ...current,
                    mode: event.target.value as MaintenanceMode,
                  }));
                }}
              >
                <option value="off">Выключен</option>
                <option value="informational">Только плашка</option>
                <option value="read_only">Только чтение</option>
                <option value="full_stop">Полная остановка</option>
              </select>
            </label>
            <label>
              <span className="field-label">Заголовок</span>
              <input
                className="input"
                value={draft.title}
                onChange={(event) => {
                  setSaved(false);
                  setDraft((current) => ({
                    ...current,
                    title: event.target.value,
                  }));
                }}
              />
            </label>
            <label className="settings-form__wide">
              <span className="field-label">Сообщение пользователю</span>
              <textarea
                className="textarea"
                rows={3}
                value={draft.message}
                onChange={(event) => {
                  setSaved(false);
                  setDraft((current) => ({
                    ...current,
                    message: event.target.value,
                  }));
                }}
              />
            </label>
            <div className="settings-form__actions">
              <span className={error ? "form-error" : "muted"}>
                {error ||
                  (saved
                    ? "Настройки сохранены"
                    : "Изменения применятся сразу")}
              </span>
              <button
                className="btn btn-primary"
                disabled={saving}
                onClick={() =>
                  void save(draft)
                    .then(() => setSaved(true))
                    .catch(() => undefined)
                }
              >
                {saving ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
