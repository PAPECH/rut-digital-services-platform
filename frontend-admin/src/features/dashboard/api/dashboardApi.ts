import { api } from "@/api/client";
import type {
  BotDashboard,
  DashboardFilters,
  PlatformDashboard,
} from "@/features/dashboard/api/types";

function query(filters: DashboardFilters): string {
  const params = new URLSearchParams();
  if (filters.dateFrom && filters.dateTo) {
    params.set("date_from", filters.dateFrom);
    params.set("date_to", filters.dateTo);
  } else {
    params.set("days", String(filters.days));
  }
  return params.toString();
}

export const dashboardApi = {
  bot: (filters: DashboardFilters) =>
    api.get<BotDashboard>(`/analytics/dashboard/bot?${query(filters)}`),
  platform: (filters: DashboardFilters) =>
    api.get<PlatformDashboard>(
      `/analytics/dashboard/platform?${query(filters)}`,
    ),
};
