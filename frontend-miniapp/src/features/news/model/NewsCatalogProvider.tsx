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
import type { NewsItem } from "@/entities/news/model/types";
import { newsApi } from "@/features/news/api/newsApi";

interface NewsCatalogState {
  items: NewsItem[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

interface NewsLoadState {
  key: string | null;
  items: NewsItem[];
  loading: boolean;
  error: string | null;
}

const NewsCatalogContext = createContext<NewsCatalogState | null>(null);

export function NewsCatalogProvider({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth();
  const catalogKey = profile ? `${getBotSlug()}:${profile.id}` : null;
  const [state, setState] = useState<NewsLoadState>({
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
      const items = await newsApi.list();
      setState({ key: catalogKey, items, loading: false, error: null });
    } catch (reason) {
      setState({
        key: catalogKey,
        items: [],
        loading: false,
        error: reason instanceof Error ? reason.message : "Не удалось загрузить новости",
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

  const value = useMemo<NewsCatalogState>(
    () => ({
      items: state.key === catalogKey ? state.items : [],
      loading: Boolean(catalogKey) && (state.loading || state.key !== catalogKey),
      error: state.key === catalogKey ? state.error : null,
      reload: async () => {
        requestedKey.current = catalogKey;
        await load();
      },
    }),
    [catalogKey, load, state],
  );

  return <NewsCatalogContext.Provider value={value}>{children}</NewsCatalogContext.Provider>;
}

export function useNewsCatalog(): NewsCatalogState {
  const value = useContext(NewsCatalogContext);
  if (!value) {
    throw new Error("useNewsCatalog used outside NewsCatalogProvider");
  }
  return value;
}
