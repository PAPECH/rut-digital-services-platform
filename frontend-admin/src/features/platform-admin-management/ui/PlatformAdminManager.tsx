import { useAuth } from "@/auth/AuthProvider";
import { AdminInviteManager } from "@/features/admin-invites/ui/AdminInviteManager";
import { usePlatformAdmins } from "@/features/platform-admin-management/model/usePlatformAdmins";
import { CreatePlatformAdminForm } from "@/features/platform-admin-management/ui/CreatePlatformAdminForm";
import { PlatformAdminList } from "@/features/platform-admin-management/ui/PlatformAdminList";

export function PlatformAdminManager() {
  const { admin } = useAuth();
  const state = usePlatformAdmins();

  return (
    <section className="card platform-admin-manager">
      <div className="card-head platform-admin-manager__head">
        <div>
          <h2 className="card-title">Администраторы платформы</h2>
          <p className="card-sub">Глобальный доступ ко всем экземплярам ботов.</p>
        </div>
        <span className="tag outline">{state.items.length}</span>
      </div>
      <div className="card-body platform-admin-manager__body">
        <CreatePlatformAdminForm
          saving={state.saving}
          externalError={state.error}
          onEnsure={state.ensure}
        />
        <div className="platform-admin-directory">
          <div className="platform-admin-directory__head">
            <strong>Текущие администраторы</strong>
            {state.loading ? <span className="muted">Обновление…</span> : null}
          </div>
          {!state.loading ? (
            <PlatformAdminList items={state.items} currentAdminId={admin?.id ?? null} />
          ) : null}
        </div>
        <AdminInviteManager scope="platform" />
      </div>
    </section>
  );
}
