import {
  INVITE_STATUS_LABELS,
  type AdminInvite,
} from "@/features/admin-invites/model/types";
import * as css from "@/features/admin-invites/ui/adminInvites.css";

const ROLE_LABELS = { employee: "Сотрудник", admin: "Администратор бота" } as const;

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AdminInviteList({
  items,
  onRevoke,
}: {
  items: AdminInvite[];
  onRevoke: (inviteId: number) => void;
}) {
  if (!items.length) {
    return <p className="muted">Приглашений пока нет.</p>;
  }

  return (
    <div className={css.list}>
      {items.map((invite) => (
        <article key={invite.id} className={css.card}>
          <div className={css.cardHead}>
            <span className={css.name}>{invite.full_name}</span>
            <span className={`${css.badge} ${css.badgeTone[invite.status]}`}>
              {INVITE_STATUS_LABELS[invite.status]}
            </span>
          </div>
          <div className={css.meta}>
            {invite.role ? <span>{ROLE_LABELS[invite.role]}</span> : null}
            <span>
              Использовано {invite.used_count} из {invite.max_uses}
            </span>
            <span>До {formatDate(invite.expires_at)}</span>
          </div>
          {invite.status === "active" ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                if (window.confirm("Отозвать приглашение? Ссылка перестанет работать.")) {
                  onRevoke(invite.id);
                }
              }}
            >
              Отозвать
            </button>
          ) : null}
        </article>
      ))}
    </div>
  );
}
