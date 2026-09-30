import { useCallback, useEffect, useState } from "react";

import { platformAdminApi } from "@/features/platform-admin-management/api/platformAdminApi";
import type {
  EnsurePlatformAdminDraft,
  PlatformAdminAccount,
} from "@/features/platform-admin-management/model/types";

export function usePlatformAdmins() {
  const [items, setItems] = useState<PlatformAdminAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await platformAdminApi.list());
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const ensure = useCallback(async (draft: EnsurePlatformAdminDraft) => {
    setSaving(true);
    setError(null);
    try {
      const result = await platformAdminApi.ensure(draft);
      setItems((current) => {
        const remaining = current.filter((item) => item.id !== result.account.id);
        return [...remaining, result.account].sort((a, b) =>
          a.full_name.localeCompare(b.full_name, "ru"),
        );
      });
      return result;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    } finally {
      setSaving(false);
    }
  }, []);

  return { items, loading, saving, error, ensure };
}
