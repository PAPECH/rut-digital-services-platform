import { useAuth } from "@/auth/AuthProvider";
import { AdminInviteManager } from "@/features/admin-invites/ui/AdminInviteManager";
import { useStaffAccess } from "@/features/staff-access/model/useStaffAccess";
import { GrantStaffAccessForm } from "@/features/staff-access/ui/GrantStaffAccessForm";
import { StaffAccessCard } from "@/features/staff-access/ui/StaffAccessCard";

export function StaffAccessManager() {
  const { admin } = useAuth();
  const { bot, items, loading, saving, error, grant, update, revoke } =
    useStaffAccess();

  return (
    <section className="staff-access-manager">
      <div className="staff-access-manager__head">
        <div>
          <h2 className="section-title staff-access-manager__title">Сотрудники бота</h2>
          <p className="page-sub">
            {bot
              ? `Доступы и права для «${bot.name}»`
              : "Доступы и права выбранного бота"}
          </p>
        </div>
        <GrantStaffAccessForm saving={saving} onGrant={grant} />
      </div>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p className="muted">Загрузка…</p> : null}
      {!loading && !items.length ? (
        <div className="card empty-state">У этого бота пока нет сотрудников.</div>
      ) : null}
      <div className="staff-access-grid">
        {items.map((access) => (
          <StaffAccessCard
            key={access.id}
            access={access}
            isSelf={admin?.id === access.admin_id}
            onUpdate={(permissions) => update(access.id, permissions)}
            onRevoke={() => revoke(access.id)}
          />
        ))}
      </div>
      <AdminInviteManager scope="bot" />
    </section>
  );
}
