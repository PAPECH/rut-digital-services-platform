import type { PlatformAdminAccount } from "@/features/platform-admin-management/model/types";

export function PlatformAdminList({
  items,
  currentAdminId,
}: {
  items: PlatformAdminAccount[];
  currentAdminId: number | null;
}) {
  if (!items.length) {
    return <div className="empty-state">Администраторы платформы пока не добавлены.</div>;
  }

  return (
    <div className="platform-admin-list">
      {items.map((item) => (
        <article key={item.id} className="platform-admin-item">
          <div className="platform-admin-item__avatar" aria-hidden="true">
            {item.full_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="platform-admin-item__identity">
            <strong>{item.full_name}</strong>
            <span>MAX ID: {item.max_user_id}</span>
          </div>
          <div className="platform-admin-item__status">
            {item.id === currentAdminId ? <span className="tag outline">Вы</span> : null}
            <span className={`tag ${item.is_active ? "done" : "neutral"}`}>
              {item.is_active ? "Активен" : "Отключён"}
            </span>
          </div>
        </article>
      ))}
    </div>
  );
}
