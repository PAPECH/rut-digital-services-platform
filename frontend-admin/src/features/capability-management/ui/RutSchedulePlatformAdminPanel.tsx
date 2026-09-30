import { useEffect, useMemo, useState } from "react";

import { getToken } from "@/api/client";
import { createAdminWebSocketUrl } from "@/api/config";
import type { CapabilityInstallation } from "@/api/types";
import {
  defaultRutScheduleConfig,
  type RutScheduleGroupWithLastSync,
  type RutScheduleInstitute,
  type RutScheduleManualSyncRequest,
} from "@/entities/capability/model/types";
import { capabilityApi } from "@/features/capability-management/api/capabilityApi";
import { getSelectedBotSlug } from "@/shared/tenant/selectedBotStorage";

type Selection = { type: "institute"; id: string } | { type: "group"; id: string } | null;

function statusLabel(status: RutScheduleManualSyncRequest["status"]) {
  if (status === "queued") return "В очереди";
  if (status === "running") return "Выполняется";
  if (status === "succeeded") return "Успешно";
  if (status === "partial") return "Частично";
  return "Ошибка";
}

function statusTagClass(status: RutScheduleManualSyncRequest["status"]) {
  if (status === "succeeded") return "success";
  if (status === "running" || status === "queued") return "neutral";
  return "danger";
}

function formatDateTime(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function scopeLabel(request: RutScheduleManualSyncRequest) {
  if (request.scope === "all") return "Все группы";
  if (request.scope === "institute") return `Институт: ${request.institute_name ?? request.institute_external_id ?? "—"}`;
  return request.group_name ?? request.group_external_id ?? "—";
}

/** Platform-admin-only manual sync controls, live log, and groups table for `rut_schedule`
 * (Task 045, extended with an institute checkbox tree + "Обновить список групп" as a follow-up).
 * Only ever rendered while the capability card is expanded -- mount/unmount doubles as the
 * WebSocket connection's open/close, matching "no background connection for admins who never
 * open this panel" from the task's UI behavior section. */
export function RutSchedulePlatformAdminPanel({
  installation,
  busy,
  onSaveConfig,
}: {
  installation: CapabilityInstallation;
  busy: string | null;
  onSaveConfig: (config: Record<string, unknown>) => Promise<void>;
}) {
  const [requests, setRequests] = useState<RutScheduleManualSyncRequest[] | null>(null);
  const [institutes, setInstitutes] = useState<RutScheduleInstitute[] | null>(null);
  const [groups, setGroups] = useState<RutScheduleGroupWithLastSync[] | null>(null);
  const [expandedInstitutes, setExpandedInstitutes] = useState<Set<string>>(new Set());
  const [selection, setSelection] = useState<Selection>(null);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [refreshingGroups, setRefreshingGroups] = useState(false);

  const loadCatalog = () => {
    capabilityApi.rutSchedule
      .institutes()
      .then(setInstitutes)
      .catch((reason) => setError((reason as Error).message || "Не удалось загрузить список институтов"));
    capabilityApi.rutSchedule
      .groups()
      .then(setGroups)
      .catch((reason) => setError((reason as Error).message || "Не удалось загрузить список групп"));
  };

  useEffect(() => {
    capabilityApi.rutSchedule
      .syncRequests()
      .then(setRequests)
      .catch((reason) => setError((reason as Error).message || "Не удалось загрузить лог синхронизации"));
    loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [installation.id]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const url = createAdminWebSocketUrl("/ws/chat");
    url.searchParams.set("token", token);
    url.searchParams.set("bot_slug", getSelectedBotSlug());
    const ws = new WebSocket(url.toString());
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.type !== "rut_schedule_sync_update") return;
        const update = parsed.data as RutScheduleManualSyncRequest;
        setRequests((current) => {
          if (!current) return [update];
          const index = current.findIndex((item) => item.id === update.id);
          if (index === -1) return [update, ...current];
          const next = [...current];
          next[index] = update;
          return next;
        });
      } catch {
        // Not a rut_schedule_sync_update payload (or malformed) -- ignore, same as every other
        // /ws/chat consumer's onmessage handler.
      }
    };
    return () => ws.close();
  }, []);

  const groupsByInstitute = useMemo(() => {
    const map = new Map<string, RutScheduleGroupWithLastSync[]>();
    for (const item of groups ?? []) {
      const list = map.get(item.group.institute_external_id);
      if (list) list.push(item);
      else map.set(item.group.institute_external_id, [item]);
    }
    return map;
  }, [groups]);

  const toggleInstituteExpanded = (externalId: string) =>
    setExpandedInstitutes((current) => {
      const next = new Set(current);
      if (next.has(externalId)) next.delete(externalId);
      else next.add(externalId);
      return next;
    });

  const refreshGroups = async () => {
    setRefreshingGroups(true);
    setError(null);
    try {
      await capabilityApi.rutSchedule.refreshGroups();
      loadCatalog();
    } catch (reason) {
      setError((reason as Error).message || "Не удалось обновить список групп");
    } finally {
      setRefreshingGroups(false);
    }
  };

  const trigger = async () => {
    if (!selection) return;
    setTriggering(true);
    setError(null);
    try {
      if (selection.type === "institute") {
        await capabilityApi.rutSchedule.triggerSyncForInstitute(selection.id);
      } else {
        await capabilityApi.rutSchedule.triggerSyncForGroup(selection.id);
      }
    } catch (reason) {
      setError((reason as Error).message || "Не удалось запустить синхронизацию");
    } finally {
      setTriggering(false);
    }
  };

  const triggerAll = async () => {
    setTriggering(true);
    setError(null);
    try {
      await capabilityApi.rutSchedule.triggerSyncForAll();
    } catch (reason) {
      setError((reason as Error).message || "Не удалось запустить синхронизацию");
    } finally {
      setTriggering(false);
    }
  };

  const config = { ...defaultRutScheduleConfig, ...installation.config } as typeof defaultRutScheduleConfig;
  const toggleNightAutoSync = () =>
    void onSaveConfig({ ...config, night_auto_sync_enabled: !config.night_auto_sync_enabled });

  const runningOrQueued = (requests ?? []).some((r) => r.status === "queued" || r.status === "running");
  const catalogLoading = institutes === null || groups === null;

  return (
    <div className="capability-platform-admin-panel">
      <h3 className="capability-platform-admin-panel__title">Синхронизация расписания</h3>
      {error ? <div className="content-status content-status--error">{error}</div> : null}

      <label className="content-checkbox capability-checkbox">
        <input
          type="checkbox"
          checked={config.night_auto_sync_enabled}
          disabled={busy !== null}
          onChange={toggleNightAutoSync}
        />
        Автоматическая синхронизация по ночам
      </label>

      <div className="capability-platform-admin-panel__section">
        <div className="capability-platform-admin-panel__tree-head">
          <h4>Институт или группа для запуска</h4>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={refreshingGroups || runningOrQueued}
            onClick={() => void refreshGroups()}
          >
            {refreshingGroups ? "Обновление…" : "Обновить список групп"}
          </button>
        </div>

        {catalogLoading ? (
          <p className="muted">Загрузка…</p>
        ) : institutes && institutes.length === 0 ? (
          <p className="muted">
            Список институтов пуст — нажмите «Обновить список групп», чтобы загрузить его с сайта.
          </p>
        ) : (
          <div className="capability-institute-tree">
            {(institutes ?? []).map((institute) => {
              const institutesGroups = groupsByInstitute.get(institute.external_id) ?? [];
              const isExpanded = expandedInstitutes.has(institute.external_id);
              return (
                <div className="capability-institute-tree__institute" key={institute.external_id}>
                  <div className="capability-institute-tree__row">
                    <button
                      type="button"
                      className="capability-institute-tree__expand"
                      aria-expanded={isExpanded}
                      aria-label={isExpanded ? "Свернуть институт" : "Развернуть институт"}
                      onClick={() => toggleInstituteExpanded(institute.external_id)}
                    >
                      {isExpanded ? "▾" : "▸"}
                    </button>
                    <label className="capability-institute-tree__label">
                      <input
                        type="radio"
                        name="rut-schedule-trigger-target"
                        checked={selection?.type === "institute" && selection.id === institute.external_id}
                        disabled={triggering || runningOrQueued}
                        onChange={() => setSelection({ type: "institute", id: institute.external_id })}
                      />
                      <strong>{institute.name}</strong>
                      <span className="muted">({institutesGroups.length} групп)</span>
                    </label>
                  </div>
                  {isExpanded ? (
                    <ul className="capability-institute-tree__groups">
                      {institutesGroups.map((item) => (
                        <li key={item.group.external_id}>
                          <label className="capability-institute-tree__label">
                            <input
                              type="radio"
                              name="rut-schedule-trigger-target"
                              checked={selection?.type === "group" && selection.id === item.group.external_id}
                              disabled={triggering || runningOrQueued}
                              onChange={() =>
                                setSelection({ type: "group", id: item.group.external_id })
                              }
                            />
                            {item.group.name}
                            <span className="muted">{formatDateTime(item.last_synced_at)}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}

        <div className="capability-platform-admin-panel__trigger">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!selection || triggering || runningOrQueued}
            onClick={() => void trigger()}
          >
            {selection?.type === "institute" ? "Запустить для института" : "Запустить для группы"}
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={triggering || runningOrQueued}
            onClick={() => void triggerAll()}
          >
            Запустить для всех групп
          </button>
        </div>
        {runningOrQueued ? (
          <p className="muted capability-health">Синхронизация уже выполняется — дождитесь завершения.</p>
        ) : null}
      </div>

      <div className="capability-platform-admin-panel__section">
        <h4>Журнал запросов</h4>
        {requests === null ? (
          <p className="muted">Загрузка…</p>
        ) : requests.length === 0 ? (
          <p className="muted">Запросов ещё не было.</p>
        ) : (
          <div className="audit-list">
            {requests.map((request) => (
              <article className="card audit-entry" key={request.id}>
                <div className="audit-entry__main">
                  <strong>
                    {request.requested_by_admin_name || `Сотрудник #${request.requested_by_admin_id ?? "—"}`}
                  </strong>
                  <span className="mono">
                    {request.provider} · {scopeLabel(request)}
                    {request.error_code ? ` · ${request.error_code}` : ""}
                  </span>
                </div>
                <div className="audit-entry__meta">
                  <span>{formatDateTime(request.requested_at)}</span>
                  {request.scope !== "group" && request.status !== "queued" && request.status !== "running" ? (
                    <span>
                      {request.groups_synced ?? 0} успешно, {request.groups_failed ?? 0} с ошибкой
                    </span>
                  ) : null}
                  <span className={`tag ${statusTagClass(request.status)}`}>{statusLabel(request.status)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="capability-platform-admin-panel__section">
        <h4>Группы и дата последней синхронизации</h4>
        {groups === null ? (
          <p className="muted">Загрузка…</p>
        ) : (
          <div className="audit-list">
            {groups.map((item) => (
              <article className="card audit-entry" key={item.group.external_id}>
                <div className="audit-entry__main">
                  <strong>{item.group.name}</strong>
                </div>
                <div className="audit-entry__meta">
                  <span>{formatDateTime(item.last_synced_at)}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
