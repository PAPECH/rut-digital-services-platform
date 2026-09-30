import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { formatDateTime } from "@/lib/status";
import { ErasureRegister } from "@/features/consent-admin/ui/ErasureRegister";

interface AuditEntry {
  id: number;
  created_at: string;
  admin_id: number | null;
  admin_name: string | null;
  method: string;
  path: string;
  status_code: number | null;
  duration_ms: number | null;
  meta: Record<string, unknown> | null;
}

const PAGE_SIZE = 50;

function operationLabel(entry: AuditEntry): string {
  const action = entry.meta?.action;
  return typeof action === "string" ? action : `${entry.method} ${entry.path}`;
}

export function AuditPage() {
  const { admin } = useAuth();
  const [tab, setTab] = useState<"actions" | "erasures">("actions");
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(
        await api.get<AuditEntry[]>(
          `/audit?limit=${PAGE_SIZE}&offset=${offset}`,
        ),
      );
      setError(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    if (tab === "actions") void load();
  }, [load, tab]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Журнал действий</h1>
          <p className="page-sub">Изменения в выбранном боте без содержимого форм и сообщений.</p>
        </div>
        {tab === "actions" ? (
          <button className="btn btn-secondary" onClick={() => void load()}>
            Обновить
          </button>
        ) : null}
      </div>

      {admin?.role === "platform_admin" ? (
        <div className="tabs" style={{ marginBottom: 16 }}>
          <button
            className={`btn ${tab === "actions" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setTab("actions")}
          >
            Действия
          </button>
          <button
            className={`btn ${tab === "erasures" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setTab("erasures")}
          >
            Удалённые аккаунты
          </button>
        </div>
      ) : null}

      {tab === "erasures" && admin?.role === "platform_admin" ? (
        <ErasureRegister />
      ) : (
        <>
          {error ? <p className="form-error">{error}</p> : null}
          {loading ? <p className="muted">Загрузка…</p> : null}
          {!loading && !items.length ? (
            <div className="card empty-state">Записей пока нет.</div>
          ) : null}

          <div className="audit-list">
            {items.map((entry) => (
              <article className="card audit-entry" key={entry.id}>
                <div className="audit-entry__main">
                  <strong>{operationLabel(entry)}</strong>
                  <span className="mono">{entry.path}</span>
                </div>
                <div className="audit-entry__meta">
                  <span>{entry.admin_name || `Сотрудник #${entry.admin_id ?? "—"}`}</span>
                  <span>{formatDateTime(entry.created_at)}</span>
                  <span className={`tag ${(entry.status_code ?? 500) < 400 ? "done" : "rej"}`}>
                    {entry.status_code ?? "—"}
                  </span>
                  <span>{entry.duration_ms === null ? "—" : `${entry.duration_ms} мс`}</span>
                </div>
              </article>
            ))}
          </div>

          <div className="audit-pagination">
            <button
              className="btn btn-secondary"
              disabled={offset === 0 || loading}
              onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
            >
              Назад
            </button>
            <span className="muted">Страница {Math.floor(offset / PAGE_SIZE) + 1}</span>
            <button
              className="btn btn-secondary"
              disabled={items.length < PAGE_SIZE || loading}
              onClick={() => setOffset((current) => current + PAGE_SIZE)}
            >
              Далее
            </button>
          </div>
        </>
      )}
    </div>
  );
}

