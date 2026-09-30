import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import type { BotInstance } from "@/api/types";

export interface CreateBotDraft {
  slug: string;
  name: string;
  description: string;
  botToken: string;
}

export function useBotInstances() {
  const [bots, setBots] = useState<BotInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const load = useCallback(async (showDeleted: boolean) => {
    setLoading(true);
    try {
      const query = showDeleted ? "?include_deleted=true" : "";
      setBots(await api.get<BotInstance[]>(`/instances${query}`));
      setError(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(includeDeleted);
  }, [load, includeDeleted]);

  const create = useCallback(async (draft: CreateBotDraft) => {
    setCreating(true);
    setError(null);
    try {
      const created = await api.post<BotInstance>("/instances", {
        slug: draft.slug,
        name: draft.name,
        description: draft.description || null,
        bot_token: draft.botToken,
        branding: {},
        settings: {
          bottom_navigation: { custom_items: [] },
          submission_table: {
            profile_fields: ["full_name", "phone", "email", "birth_date"],
          },
        },
        profile_schema: [],
      });
      setBots((current) => [...current, created]);
      return created;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    } finally {
      setCreating(false);
    }
  }, []);

  const update = useCallback(
    async (
      botId: number,
      patch: Partial<
        Pick<
          BotInstance,
          | "name"
          | "description"
          | "is_active"
          | "order"
          | "branding"
          | "settings"
          | "profile_schema"
        >
      >,
    ) => {
      setError(null);
      try {
        const updated = await api.patch<BotInstance>(`/instances/${botId}`, patch);
        setBots((current) =>
          current
            .map((bot) => (bot.id === updated.id ? updated : bot))
            .sort((a, b) => a.order - b.order || a.id - b.id),
        );
        return updated;
      } catch (reason) {
        setError((reason as Error).message);
        throw reason;
      }
    },
    [],
  );

  const remove = useCallback(async (botId: number) => {
    setError(null);
    try {
      const deleted = await api.del<BotInstance>(`/instances/${botId}`);
      setBots((current) =>
        includeDeleted
          ? current.map((bot) => (bot.id === deleted.id ? deleted : bot))
          : current.filter((bot) => bot.id !== botId),
      );
      return deleted;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    }
  }, [includeDeleted]);

  const restore = useCallback(async (botId: number) => {
    setError(null);
    try {
      const restored = await api.post<BotInstance>(`/instances/${botId}/restore`);
      setBots((current) => current.map((bot) => (bot.id === restored.id ? restored : bot)));
      return restored;
    } catch (reason) {
      setError((reason as Error).message);
      throw reason;
    }
  }, []);

  return {
    bots,
    loading,
    creating,
    error,
    includeDeleted,
    setIncludeDeleted,
    create,
    update,
    remove,
    restore,
  };
}
