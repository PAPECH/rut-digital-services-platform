import { useCallback, useEffect, useState } from "react";

import { dashboardApi } from "@/features/dashboard/api/dashboardApi";
import type {
  BotDashboard,
  DashboardFilters,
  DashboardScope,
  PlatformDashboard,
} from "@/features/dashboard/api/types";

export type DashboardSnapshot =
  | { scope: "bot"; data: BotDashboard }
  | { scope: "platform"; data: PlatformDashboard };

interface DashboardRequestState {
  requestKey: string;
  snapshot: DashboardSnapshot | null;
  loading: boolean;
  error: string | null;
}

function buildRequestKey(
  scope: DashboardScope,
  filters: DashboardFilters,
  selectedBotSlug: string,
): string {
  const target = scope === "bot" ? selectedBotSlug : "all-bots";
  return [
    scope,
    target,
    filters.days,
    filters.dateFrom,
    filters.dateTo,
  ].join(":");
}

async function loadDashboard(
  scope: DashboardScope,
  filters: DashboardFilters,
): Promise<DashboardSnapshot> {
  if (scope === "platform") {
    return { scope, data: await dashboardApi.platform(filters) };
  }
  return { scope, data: await dashboardApi.bot(filters) };
}

export function useDashboardData(
  scope: DashboardScope,
  filters: DashboardFilters,
  selectedBotSlug: string,
) {
  const requestKey = buildRequestKey(scope, filters, selectedBotSlug);
  const [state, setState] = useState<DashboardRequestState>({
    requestKey: "",
    snapshot: null,
    loading: true,
    error: null,
  });
  const [revision, setRevision] = useState(0);
  const retry = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let cancelled = false;
    setState({ requestKey, snapshot: null, loading: true, error: null });
    void loadDashboard(scope, filters)
      .then((snapshot) => {
        if (!cancelled) {
          setState({ requestKey, snapshot, loading: false, error: null });
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setState({
            requestKey,
            snapshot: null,
            loading: false,
            error:
              reason instanceof Error
                ? reason.message
                : "Не удалось загрузить статистику",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filters, requestKey, revision, scope]);

  if (state.requestKey !== requestKey) {
    return { snapshot: null, loading: true, error: null, retry };
  }
  return {
    snapshot: state.snapshot,
    loading: state.loading,
    error: state.error,
    retry,
  };
}
