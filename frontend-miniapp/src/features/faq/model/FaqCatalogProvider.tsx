import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { getBotSlug } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import type { FaqItem } from "@/entities/faq/model/types";
import { faqApi } from "@/features/faq/api/faqApi";

interface FaqCatalogState {
  items: FaqItem[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

interface FaqLoadState {
  key: string | null;
  items: FaqItem[];
  loading: boolean;
  error: string | null;
}

const FaqCatalogContext = createContext<FaqCatalogState | null>(null);

export function FaqCatalogProvider({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth();
  const catalogKey = profile ? `${getBotSlug()}:${profile.id}` : null;
  const [state, setState] = useState<FaqLoadState>({
    key: null,
    items: [],
    loading: false,
    error: null,
  });
  const requestedKey = useRef<string | null>(null);

  const load = useCallback(async () => {
    if (!catalogKey) return;
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const items = await faqApi.list();
      setState({ key: catalogKey, items, loading: false, error: null });
    } catch (reason) {
      setState({
        key: catalogKey,
        items: [],
        loading: false,
        error:
          reason instanceof Error
            ? reason.message
            : "Не удалось загрузить частые вопросы",
      });
    }
  }, [catalogKey]);

  useEffect(() => {
    if (!catalogKey) {
      requestedKey.current = null;
      setState({ key: null, items: [], loading: false, error: null });
      return;
    }
    if (requestedKey.current === catalogKey) return;
    requestedKey.current = catalogKey;
    void load();
  }, [catalogKey, load]);

  const value = useMemo<FaqCatalogState>(() => ({
    items: state.key === catalogKey ? state.items : [],
    loading: Boolean(catalogKey) && (state.loading || state.key !== catalogKey),
    error: state.key === catalogKey ? state.error : null,
    reload: async () => {
      requestedKey.current = catalogKey;
      await load();
    },
  }), [catalogKey, load, state]);

  return (
    <FaqCatalogContext.Provider value={value}>
      {children}
    </FaqCatalogContext.Provider>
  );
}

export function useFaqCatalog(): FaqCatalogState {
  const value = useContext(FaqCatalogContext);
  if (!value) {
    throw new Error("useFaqCatalog used outside FaqCatalogProvider");
  }
  return value;
}
