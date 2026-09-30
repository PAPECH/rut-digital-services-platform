import { useCallback, useEffect, useState } from "react";

import { adminInviteApi } from "@/features/admin-invites/api/adminInviteApi";
import type {
  AdminInvite,
  AdminInviteDraft,
  InviteScope,
} from "@/features/admin-invites/model/types";

export function useAdminInvites(scope: InviteScope) {
  const [items, setItems] = useState<AdminInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await adminInviteApi.list(scope));
      setError(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (draft: AdminInviteDraft) => {
      setSaving(true);
      try {
        const created = await adminInviteApi.create(scope, draft);
        setItems((current) => [created.invite, ...current]);
        return created;
      } finally {
        setSaving(false);
      }
    },
    [scope],
  );

  const revoke = useCallback(
    async (inviteId: number) => {
      try {
        await adminInviteApi.revoke(scope, inviteId);
        setItems((current) =>
          current.map((item) =>
            item.id === inviteId
              ? { ...item, status: "revoked", revoked_at: new Date().toISOString() }
              : item,
          ),
        );
      } catch (reason) {
        setError((reason as Error).message);
      }
    },
    [scope],
  );

  return { items, loading, saving, error, create, revoke };
}
