import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/api/client";
import type { BotInstance } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import {
  BotSelectionContext,
  type BotSelectionState,
} from "@/features/bot-selection/model/BotSelectionContext";
import {
  getSelectedBotSlug,
  persistSelectedBotSlug,
} from "@/shared/tenant/selectedBotStorage";

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Не удалось загрузить список ботов";
}

export function BotSelectionProvider({ children }: { children: ReactNode }) {
  const { admin } = useAuth();
  const [bots, setBots] = useState<BotInstance[]>([]);
  const [selectedSlug, setSelectedSlug] = useState(getSelectedBotSlug);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectBot = useCallback((slug: string) => {
    const normalizedSlug = slug.trim().toLowerCase();
    if (!normalizedSlug) return;
    persistSelectedBotSlug(normalizedSlug);
    setSelectedSlug(normalizedSlug);
  }, []);

  const reloadBots = useCallback(async () => {
    if (!admin) {
      setBots([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const availableBots = await api.get<BotInstance[]>("/instances");
      setBots(availableBots);

      const storedSlug = getSelectedBotSlug();
      const nextSlug = availableBots.some((bot) => bot.slug === storedSlug)
        ? storedSlug
        : availableBots[0]?.slug;
      if (nextSlug) selectBot(nextSlug);
    } catch (reason) {
      setBots([]);
      setError(getErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [admin, selectBot]);

  useEffect(() => {
    void reloadBots();
  }, [reloadBots]);

  const value = useMemo<BotSelectionState>(
    () => ({ bots, selectedSlug, loading, error, selectBot, reloadBots }),
    [bots, selectedSlug, loading, error, selectBot, reloadBots],
  );

  return (
    <BotSelectionContext.Provider value={value}>
      {children}
    </BotSelectionContext.Provider>
  );
}
