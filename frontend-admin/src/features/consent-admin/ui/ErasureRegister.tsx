import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import { formatDateTime } from "@/lib/status";

interface ConsentEvent {
  event_type: "given" | "revoked" | "deletion_executed";
  occurred_at: string;
  policy_version: string | null;
}

interface ErasureEntry {
  external_user_id: string;
  system: string;
  given_at: string | null;
  revoked_at: string | null;
  deleted_at: string | null;
  events: ConsentEvent[];
}

const PAGE_SIZE = 50;

const EVENT_LABEL: Record<ConsentEvent["event_type"], string> = {
  given: "Согласие получено",
  revoked: "Согласие отозвано",
  deletion_executed: "Данные удалены",
};

// Platform-admin-only durable erasure register (Task 064) -- proof that a given/revoke/
// delete cycle happened, without reconstructing any of the deleted person's profile
// content: only the external identity key and the three timestamps survive.
export function ErasureRegister() {
  const [items, setItems] = useState<ErasureEntry[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(
        await api.get<ErasureEntry[]>(
          `/consent/admin/erasures?limit=${PAGE_SIZE}&offset=${offset}`,
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
    void load();
  }, [load]);

  return (
    <div>
      <p className="page-sub">
        Личности, чьи данные были полностью удалены платформой по истечении 10 рабочих
        дней после отзыва согласия. Профильные данные не восстанавливаются — ниже только
        факт и даты.
      </p>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p className="muted">Загрузка…</p> : null}
      {!loading && !items.length ? (
        <div className="card empty-state">Удалений пока не было.</div>
      ) : null}

      <div className="audit-list">
        {items.map((entry) => (
          <article
            className="card audit-entry"
            key={`${entry.system}:${entry.external_user_id}`}
          >
            <div className="audit-entry__main">
              <strong className="mono">
                {entry.system}:{entry.external_user_id}
              </strong>
              <span>
                {entry.given_at ? `согласие с ${formatDateTime(entry.given_at)}` : ""}
              </span>
            </div>
            <div className="audit-entry__meta" style={{ flexDirection: "column", alignItems: "flex-start" }}>
              {entry.events.map((event, idx) => (
                <span key={idx}>
                  {EVENT_LABEL[event.event_type]} — {formatDateTime(event.occurred_at)}
                </span>
              ))}
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
    </div>
  );
}
