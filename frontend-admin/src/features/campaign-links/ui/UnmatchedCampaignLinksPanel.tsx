import type {
  UnmatchedCampaignLink,
  UnmatchedCampaignLinkSource,
} from "@/entities/campaign-links/model/types";
import { formatDateTime } from "@/lib/status";

const SOURCE_LABEL: Record<UnmatchedCampaignLinkSource, string> = {
  bot_started: "Первый запуск бота",
  bot_repeat: "Повторный /start",
  webapp: "Мини-приложение",
};

interface Props {
  items: UnmatchedCampaignLink[];
  loading: boolean;
  error: string | null;
}

// Read-only: an admin decides whether a raw code is worth creating a matching campaign link for
// (see Task 074) -- no manual-entry shortcut here, this is purely what the system already
// captured (guardrails' "minimize manual entry" rule).
export function UnmatchedCampaignLinksPanel({ items, loading, error }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <strong>Несопоставленные переходы</strong>
        <p className="page-sub" style={{ margin: 0 }}>
          Коды, полученные ботом или мини-приложением, для которых нет активной кампанейской
          ссылки — например, опечатка в постере или ссылка, созданная раньше кампании.
        </p>
      </div>
      <div className="card-body">
        {error ? <p className="form-error">{error}</p> : null}
        <div className="content-files-table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Код</th>
                <th>Откуда</th>
                <th>Попыток</th>
                <th>Последний раз</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={`${item.code}:${item.event_source}`}>
                  <td className="mono">{item.code}</td>
                  <td>{SOURCE_LABEL[item.event_source]}</td>
                  <td>{item.hit_count}</td>
                  <td>{formatDateTime(item.last_seen_at)}</td>
                </tr>
              ))}
              {!loading && items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted">
                    Несопоставленных переходов пока нет
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {loading ? <p className="muted">Загрузка…</p> : null}
      </div>
    </div>
  );
}
