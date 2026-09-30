import { useCallback, useEffect, useState } from "react";

import type { ApiError } from "@/api/client";
import type {
  CampaignLink,
  CampaignLinkCreateInput,
} from "@/entities/campaign-links/model/types";
import { campaignLinksApi } from "@/features/campaign-links/api/campaignLinksApi";

export function useCampaignLinks() {
  const [items, setItems] = useState<CampaignLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    campaignLinksApi
      .list()
      .then(setItems)
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error ? reason.message : "Не удалось загрузить ссылки",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const create = useCallback(
    async (
      input: CampaignLinkCreateInput,
    ): Promise<{ ok: true } | { ok: false; message: string; code?: string }> => {
      setCreating(true);
      try {
        await campaignLinksApi.create(input);
        reload();
        return { ok: true };
      } catch (reason) {
        const apiError = reason as ApiError;
        return {
          ok: false,
          message: apiError.message || "Не удалось создать ссылку",
          code: apiError.code,
        };
      } finally {
        setCreating(false);
      }
    },
    [reload],
  );

  const remove = useCallback(
    async (id: number): Promise<boolean> => {
      setDeletingId(id);
      try {
        await campaignLinksApi.remove(id);
        reload();
        return true;
      } catch (reason) {
        setError(
          reason instanceof Error ? reason.message : "Не удалось удалить ссылку",
        );
        return false;
      } finally {
        setDeletingId(null);
      }
    },
    [reload],
  );

  return { items, loading, error, creating, deletingId, create, remove, reload };
}
