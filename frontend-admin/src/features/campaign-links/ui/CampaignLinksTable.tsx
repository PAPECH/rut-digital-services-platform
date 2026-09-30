import type { CampaignLink } from "@/entities/campaign-links/model/types";
import { formatDateTime } from "@/lib/status";

interface Props {
  items: CampaignLink[];
  loading: boolean;
  deletingId: number | null;
  onDelete: (link: CampaignLink) => void;
  onPrint: (link: CampaignLink) => void;
}

export function CampaignLinksTable({ items, loading, deletingId, onDelete, onPrint }: Props) {
  return (
    <div className="content-files-table-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>Кампания</th>
            <th>Источник</th>
            <th>Размещение</th>
            <th>Куда ведёт</th>
            <th>Первые</th>
            <th>Повторные</th>
            <th>Уникальных</th>
            <th>Создана</th>
            <th aria-hidden="true" />
          </tr>
        </thead>
        <tbody>
          {items.map((link) => (
            <tr key={link.id}>
              <td>{link.campaign}</td>
              <td>{link.source}</td>
              <td>{link.placement}</td>
              <td>{link.target === "webapp" ? "Мини-приложение" : "Чат бота"}</td>
              <td>{link.first_open_count}</td>
              <td>{link.target === "bot" ? link.repeat_open_count : "—"}</td>
              <td>{link.unique_open_count}</td>
              <td>{formatDateTime(link.created_at)}</td>
              <td>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => void navigator.clipboard.writeText(link.deep_link)}
                  >
                    Скопировать ссылку
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => onPrint(link)}
                  >
                    Печать
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={deletingId === link.id}
                    onClick={() => onDelete(link)}
                  >
                    {deletingId === link.id ? "Удаление…" : "Удалить"}
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 ? (
            <tr>
              <td colSpan={9} className="muted">
                Кампанейских ссылок пока нет
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
      {loading ? <p className="muted">Загрузка…</p> : null}
    </div>
  );
}
