import { createContext, useContext } from "react";

import type { BotInstance } from "@/api/types";

export interface BotSelectionState {
  bots: BotInstance[];
  selectedSlug: string;
  loading: boolean;
  error: string | null;
  selectBot: (slug: string) => void;
  reloadBots: () => Promise<void>;
}

export const BotSelectionContext = createContext<BotSelectionState | null>(null);

export function useBotSelection(): BotSelectionState {
  const context = useContext(BotSelectionContext);
  if (!context) {
    throw new Error("useBotSelection must be used within BotSelectionProvider");
  }
  return context;
}
