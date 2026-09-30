import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import type { MaintenanceMode, MaintenancePolicy } from "@/api/types";

export interface MaintenanceDraft {
  mode: MaintenanceMode;
  title: string;
  message: string;
  retry_after_seconds: number | null;
  allow_admin: boolean;
}

export function useMaintenancePolicy(
  endpoint: "/maintenance/current" | "/maintenance/global",
) {
  const [policy, setPolicy] = useState<MaintenancePolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPolicy(await api.get<MaintenancePolicy>(endpoint));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(
    async (draft: MaintenanceDraft) => {
      setSaving(true);
      setError(null);
      try {
        const updated = await api.patch<MaintenancePolicy>(endpoint, {
          ...draft,
          starts_at: null,
          ends_at: null,
        });
        setPolicy(updated);
      } catch (reason) {
        setError((reason as Error).message);
        throw reason;
      } finally {
        setSaving(false);
      }
    },
    [endpoint],
  );

  return { policy, loading, saving, error, save };
}
