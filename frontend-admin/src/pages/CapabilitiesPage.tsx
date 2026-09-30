import { useState } from "react";

import { useAuth } from "@/auth/AuthProvider";
import { useCapabilities } from "@/features/capability-management/model/useCapabilities";
import { CapabilityEditorRegistry } from "@/features/capability-management/ui/editors/CapabilityEditorRegistry";
import { RutSchedulePlatformAdminPanel } from "@/features/capability-management/ui/RutSchedulePlatformAdminPanel";

function healthLabel(value: string) {
  if (value === "healthy") return "Работает";
  if (value === "degraded") return "Ошибка подключения";
  if (value === "unknown") return "Не проверено";
  return "Не настроено";
}

export function CapabilitiesPage() {
  const { admin } = useAuth();
  const capabilities = useCapabilities();
  const platformAdmin = admin?.role === "platform_admin";
  // Collapsed by default (see Task 045: "всё свалено на одном экране") -- independent per card,
  // not persisted across a page reload.
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const toggleExpanded = (key: string) =>
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Возможности бота</h1>
          <p className="page-sub">
            Подключаемые функции, установленные вместе с платформой.
          </p>
        </div>
      </div>
      {capabilities.error ? (
        <div className="content-status content-status--error">
          <span>{capabilities.error}</span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => void capabilities.reload()}
          >
            Обновить
          </button>
        </div>
      ) : null}
      {capabilities.notice ? (
        <div className="content-status content-status--success">
          {capabilities.notice}
        </div>
      ) : null}
      {capabilities.loading ? <p className="muted">Загрузка…</p> : null}
      <div className="capability-list">
        {capabilities.installations.map((installation, index) => {
          const isExpanded = expandedKeys.has(installation.capability_key);
          return (
            <section
              className="card capability-card"
              key={installation.capability_key}
            >
              <div className="card-head capability-card-head">
                <button
                  type="button"
                  className="capability-card-toggle"
                  aria-expanded={isExpanded}
                  onClick={() => toggleExpanded(installation.capability_key)}
                >
                  <div>
                    <div className="capability-title-row">
                      <h2 className="card-title">{installation.name}</h2>
                      <span
                        className={`tag ${installation.is_enabled ? "success" : "neutral"}`}
                      >
                        {installation.is_enabled ? "Включено" : "Отключено"}
                      </span>
                      <span
                        className={`tag ${installation.last_health_status === "degraded" ? "danger" : "neutral"}`}
                      >
                        {healthLabel(installation.last_health_status)}
                      </span>
                    </div>
                    <p className="card-sub">
                      {installation.description} · версия {installation.version}
                    </p>
                  </div>
                  <span className="capability-card-chevron" aria-hidden="true">
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </button>
                {platformAdmin ? (
                  <div className="capability-card-controls">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      aria-label="Поднять возможность"
                      disabled={
                        index === 0 ||
                        capabilities.busy !== null ||
                        installation.id === null
                      }
                      onClick={() =>
                        void capabilities.move(installation.capability_key, -1)
                      }
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      aria-label="Опустить возможность"
                      disabled={
                        index === capabilities.installations.length - 1 ||
                        capabilities.busy !== null ||
                        installation.id === null
                      }
                      onClick={() =>
                        void capabilities.move(installation.capability_key, 1)
                      }
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      className={`btn ${installation.is_enabled ? "btn-danger" : "btn-primary"}`}
                      disabled={
                        capabilities.busy !== null ||
                        (!installation.is_enabled && installation.id === null)
                      }
                      onClick={() =>
                        void (installation.is_enabled
                          ? capabilities.disable(installation)
                          : capabilities.enable(installation))
                      }
                    >
                      {installation.is_enabled ? "Отключить" : "Включить"}
                    </button>
                  </div>
                ) : null}
              </div>
              {isExpanded ? (
                <div className="card-body">
                  <CapabilityEditorRegistry
                    installation={installation}
                    busy={capabilities.busy}
                    onSave={(config) => capabilities.save(installation, config)}
                    onTest={() => capabilities.test(installation)}
                  />
                  {platformAdmin &&
                  installation.capability_key === "rut_schedule" &&
                  installation.is_enabled ? (
                    <RutSchedulePlatformAdminPanel
                      installation={installation}
                      busy={capabilities.busy}
                      onSaveConfig={(config) => capabilities.save(installation, config)}
                    />
                  ) : null}
                  {platformAdmin && installation.id === null ? (
                    <p className="muted capability-health">
                      Сначала заполните и сохраните настройки, затем возможность
                      можно будет включить.
                    </p>
                  ) : null}
                  {installation.last_health_at ? (
                    <p className="muted capability-health">
                      Последняя проверка:{" "}
                      {new Date(installation.last_health_at).toLocaleString(
                        "ru-RU",
                      )}
                      {installation.last_health_error_code
                        ? ` · ${installation.last_health_error_code}`
                        : ""}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}
