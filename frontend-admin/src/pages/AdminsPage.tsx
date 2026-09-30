import { useAuth } from "@/auth/AuthProvider";
import { PlatformAdminManager } from "@/features/platform-admin-management/ui/PlatformAdminManager";
import { StaffAccessManager } from "@/features/staff-access/ui/StaffAccessManager";

export function AdminsPage() {
  const { admin } = useAuth();
  return (
    <div className="page staff-management-page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Сотрудники и доступы</h1>
          <p className="page-sub">Глобальные роли и права внутри выбранного бота.</p>
        </div>
      </div>
      {admin?.role === "platform_admin" ? <PlatformAdminManager /> : null}
      <StaffAccessManager />
    </div>
  );
}
