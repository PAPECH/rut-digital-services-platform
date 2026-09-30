import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { TicketsOverview } from "@/api/types";

export function useTicketsOverview(enabled: boolean, tenantKey: string): number {
  const [ticketsCount, setTicketsCount] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const load = () => {
      api
        .get<TicketsOverview>("/tickets/overview")
        .then((result) => setTicketsCount(result.open_count))
        .catch(() => setTicketsCount(0));
    };
    load();
    const timer = window.setInterval(load, 20_000);
    return () => window.clearInterval(timer);
  }, [enabled, tenantKey]);

  return ticketsCount;
}
