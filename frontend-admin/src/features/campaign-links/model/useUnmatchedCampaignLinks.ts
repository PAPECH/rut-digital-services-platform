import { useCallback, useEffect, useState } from "react";

import type { UnmatchedCampaignLink } from "@/entities/campaign-links/model/types";
import { campaignLinksApi } from "@/features/campaign-links/api/campaignLinksApi";

export function useUnmatchedCampaignLinks() {
  const [items, setItems] = useState<UnmatchedCampaignLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    campaignLinksApi
      .unmatched()
      .then(setItems)
      .catch((reason: unknown) => {
        setError(
          reason instanceof Error ? reason.message : "Не удалось загрузить несопоставленные переходы",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, loading, error, reload };
}
