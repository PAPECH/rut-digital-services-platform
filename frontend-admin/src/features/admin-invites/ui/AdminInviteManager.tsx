import type { InviteScope } from "@/features/admin-invites/model/types";
import { useAdminInvites } from "@/features/admin-invites/model/useAdminInvites";
import { AdminInviteList } from "@/features/admin-invites/ui/AdminInviteList";
import * as css from "@/features/admin-invites/ui/adminInvites.css";
import { CreateInviteDialog } from "@/features/admin-invites/ui/CreateInviteDialog";

export function AdminInviteManager({ scope }: { scope: InviteScope }) {
  const { items, loading, saving, error, create, revoke } = useAdminInvites(scope);

  return (
    <section className={css.section}>
      <div className={css.head}>
        <h3 className={css.title}>Приглашения по ссылке</h3>
        <CreateInviteDialog scope={scope} saving={saving} onCreate={create} />
      </div>
      {error ? <p className="form-error">{error}</p> : null}
      {loading ? (
        <p className="muted">Загрузка…</p>
      ) : (
        <AdminInviteList items={items} onRevoke={(id) => void revoke(id)} />
      )}
    </section>
  );
}
