import { useEffect, useState } from "react";

import type { DashboardFilters } from "@/features/dashboard/api/types";

const STORAGE_KEY = "platform.dashboard.filters";
const DEFAULT_FILTERS: DashboardFilters = {
  days: 30,
  dateFrom: "",
  dateTo: "",
};

function initialFilters(): DashboardFilters {
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "null") as
      | Partial<DashboardFilters>
      | null;
    if (!stored || ![7, 30, 90].includes(Number(stored.days))) return DEFAULT_FILTERS;
    return {
      days: Number(stored.days) as 7 | 30 | 90,
      dateFrom: typeof stored.dateFrom === "string" ? stored.dateFrom : "",
      dateTo: typeof stored.dateTo === "string" ? stored.dateTo : "",
    };
  } catch {
    return DEFAULT_FILTERS;
  }
}

export function useDashboardFilters() {
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  const selectDays = (days: 7 | 30 | 90) =>
    setFilters({ days, dateFrom: "", dateTo: "" });
  const setDateFrom = (dateFrom: string) =>
    setFilters((current) => ({ ...current, dateFrom }));
  const setDateTo = (dateTo: string) =>
    setFilters((current) => ({ ...current, dateTo }));

  return { filters, selectDays, setDateFrom, setDateTo };
}
