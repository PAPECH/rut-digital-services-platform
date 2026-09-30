import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { SubmissionsPage } from "@/pages/SubmissionsPage";
import { FormTestsPage } from "@/pages/FormTestsPage";
import { TicketsPage } from "@/pages/TicketsPage";
import { UsersPage } from "@/pages/UsersPage";
import { BuilderPage } from "@/pages/BuilderPage";
import { AdminsPage } from "@/pages/AdminsPage";
import { BotSettingsPage } from "@/pages/BotSettingsPage";
import { FaqPage } from "@/pages/FaqPage";
import { KbPage } from "@/pages/KbPage";
import { PlatformBotsPage } from "@/pages/PlatformBotsPage";
import { ContentBuilderPage } from "@/pages/ContentBuilderPage";
import { NewsPage } from "@/pages/NewsPage";
import { FilesPage } from "@/pages/FilesPage";
import { CapabilitiesPage } from "@/pages/CapabilitiesPage";
import { CampaignLinksPage } from "@/pages/CampaignLinksPage";
import { AuditPage } from "@/pages/AuditPage";
import { GuidePage } from "@/pages/GuidePage";

function Guard({ children }: { children: React.ReactNode }) {
  const { admin, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ padding: 32, color: "var(--ink-400)" }}>
        Загрузка… / Loading…
      </div>
    );
  }
  if (!admin) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { admin } = useAuth();
  if (admin?.role !== "admin" && admin?.role !== "platform_admin") {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function PlatformAdminOnly({ children }: { children: React.ReactNode }) {
  const { admin } = useAuth();
  if (admin?.role !== "platform_admin")
    return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <Guard>
            <Layout>
              <Routes>
                <Route
                  path="/"
                  element={<Navigate to="/dashboard" replace />}
                />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/submissions" element={<SubmissionsPage />} />
                <Route path="/form-tests" element={<FormTestsPage />} />
                <Route path="/tickets" element={<TicketsPage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route
                  path="/platform/bots"
                  element={
                    <PlatformAdminOnly>
                      <PlatformBotsPage />
                    </PlatformAdminOnly>
                  }
                />
                <Route
                  path="/builder"
                  element={
                    <AdminOnly>
                      <BuilderPage />
                    </AdminOnly>
                  }
                />
                <Route path="/content" element={<ContentBuilderPage />} />
                <Route path="/files" element={<FilesPage />} />
                <Route path="/capabilities" element={<CapabilitiesPage />} />
                <Route
                  path="/campaigns"
                  element={
                    <AdminOnly>
                      <CampaignLinksPage />
                    </AdminOnly>
                  }
                />
                <Route
                  path="/audit"
                  element={
                    <AdminOnly>
                      <AuditPage />
                    </AdminOnly>
                  }
                />
                <Route
                  path="/admins"
                  element={
                    <AdminOnly>
                      <AdminsPage />
                    </AdminOnly>
                  }
                />
                <Route
                  path="/bot-settings"
                  element={
                    <AdminOnly>
                      <BotSettingsPage />
                    </AdminOnly>
                  }
                />
                <Route
                  path="/faq"
                  element={
                    <AdminOnly>
                      <FaqPage />
                    </AdminOnly>
                  }
                />
                <Route path="/news" element={<NewsPage />} />
                <Route path="/guide" element={<GuidePage />} />
                <Route
                  path="/kb"
                  element={
                    <AdminOnly>
                      <KbPage />
                    </AdminOnly>
                  }
                />
                <Route
                  path="*"
                  element={<Navigate to="/dashboard" replace />}
                />
              </Routes>
            </Layout>
          </Guard>
        }
      />
    </Routes>
  );
}
