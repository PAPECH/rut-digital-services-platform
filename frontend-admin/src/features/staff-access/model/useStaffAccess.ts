import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import type { BotInstance } from "@/api/types";
import type {
  GrantStaffAccessDraft,
  StaffAccess,
  StaffPermissions,
} from "@/features/staff-access/model/types";

export function useStaffAccess() {
  const [bot, setBot] = useState<BotInstance | null>(null);
  const [items, setItems] = useState<StaffAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [currentBot, staff] = await Promise.all([
        api.get<BotInstance>("/instances/current"),
        api.get<StaffAccess[]>("/instances/current/staff-access"),
      ]);
      setBot(currentBot);
      setItems(staff);
      setError(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grant = useCallback(async (draft: GrantStaffAccessDraft) => {
    setSaving(true);
    setError(null);
    try {
      const created = await api.post<StaffAccess>(
        "/instances/current/staff-access",
        draft,
      );
      setItems((current) =>
        [...current, created].sort((a, b) =>
          a.full_name.localeCompare(b.full_name, "ru"),
        ),
      );
      return created;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    } finally {
      setSaving(false);
    }
  }, []);

  const update = useCallback(
    async (accessId: number, permissions: StaffPermissions) => {
      const updated = await api.patch<StaffAccess>(
        `/instances/current/staff-access/${accessId}`,
        { permissions },
      );
      setItems((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      return updated;
    },
    [],
  );

  const revoke = useCallback(async (accessId: number) => {
    await api.del(`/instances/current/staff-access/${accessId}`);
    setItems((current) => current.filter((item) => item.id !== accessId));
  }, []);

  return { bot, items, loading, saving, error, grant, update, revoke };
}

