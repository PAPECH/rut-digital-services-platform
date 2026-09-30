import { useEffect, useState } from "react";

import { useAuth } from "@/auth/AuthProvider";
import { useBotSelection } from "@/features/bot-selection/model/BotSelectionContext";
import type { DashboardScope } from "@/features/dashboard/api/types";
import { useDashboardData } from "@/features/dashboard/model/useDashboardData";
import { useDashboardFilters } from "@/features/dashboard/model/useDashboardFilters";
import { BotDashboardView } from "@/features/dashboard/ui/BotDashboardView";
import { DashboardFilters } from "@/features/dashboard/ui/DashboardFilters";
import {
  DashboardError,
  DashboardLoading,
} from "@/features/dashboard/ui/DashboardState";
import { PlatformDashboardView } from "@/features/dashboard/ui/PlatformDashboardView";

const SCOPE_KEY = "platform.dashboard.scope";

function initialScope(platformAdmin: boolean): DashboardScope {
  if (!platformAdmin) return "bot";
  return sessionStorage.getItem(SCOPE_KEY) === "bot" ? "bot" : "platform";
}

export function DashboardPage() {
  const { admin } = useAuth();
  const platformAdmin = admin?.role === "platform_admin";
  const { bots, selectedSlug, selectBot } = useBotSelection();
  const selectedBot = bots.find((bot) => bot.slug === selectedSlug);
  const [scope, setScope] = useState<DashboardScope>(() =>
    initialScope(platformAdmin),
  );
  const { filters, selectDays, setDateFrom, setDateTo } =
    useDashboardFilters();
  const { snapshot, loading, error, retry } = useDashboardData(
    scope,
    filters,
    selectedSlug,
  );

  useEffect(() => {
    if (!platformAdmin && scope !== "bot") setScope("bot");
  }, [platformAdmin, scope]);

  const changeScope = (next: DashboardScope) => {
    const allowed = platformAdmin ? next : "bot";
    sessionStorage.setItem(SCOPE_KEY, allowed);
    setScope(allowed);
  };

  const openBot = (slug: string) => {
    sessionStorage.setItem(SCOPE_KEY, "bot");
    setScope("bot");
    selectBot(slug);
  };

  return (
    <div className="page dashboard-page">
      <div className="page-head dashboard-page-head">
        <div>
          <h1 className="page-title">
            {scope === "platform"
              ? "Дашборд платформы"
              : `Дашборд${selectedBot ? ` — ${selectedBot.name}` : ""}`}
          </h1>
          <p className="page-sub">
            {scope === "platform"
              ? "Общие показатели и сравнение всех ботов"
              : "Пользователи, формы, клики по контенту, возможности и обращения выбранного бота"}
          </p>
        </div>
        <DashboardFilters
          platformAdmin={platformAdmin}
          scope={scope}
          filters={filters}
          onScope={changeScope}
          onDays={selectDays}
          onDateFrom={setDateFrom}
          onDateTo={setDateTo}
        />
      </div>

      {loading ? <DashboardLoading /> : null}
      {!loading && error ? <DashboardError message={error} onRetry={retry} /> : null}
      {!loading && !error && snapshot?.scope === "platform" ? (
        <PlatformDashboardView
          data={snapshot.data}
          onOpenBot={openBot}
        />
      ) : null}
      {!loading && !error && snapshot?.scope === "bot" ? (
        <BotDashboardView data={snapshot.data} />
      ) : null}
    </div>
  );
}
