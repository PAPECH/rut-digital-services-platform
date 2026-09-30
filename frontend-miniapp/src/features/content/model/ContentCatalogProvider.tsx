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
import type {
  PublishedCategorySummary,
  PublishedContent,
} from "@/entities/content/model/types";
import { contentApi } from "@/features/content/api/contentApi";
import { warmImageCache } from "@/lib/imageCache";

interface ContentCatalogState {
  contents: PublishedContent[];
  categories: PublishedCategorySummary[];
  bySlug: ReadonlyMap<string, PublishedContent>;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

interface CatalogLoadState {
  key: string | null;
  contents: PublishedContent[];
  loading: boolean;
  error: string | null;
}

const ContentCatalogContext = createContext<ContentCatalogState | null>(null);

export function ContentCatalogProvider({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth();
  const catalogKey = profile ? `${getBotSlug()}:${profile.id}` : null;
  const [state, setState] = useState<CatalogLoadState>({
    key: null,
    contents: [],
    loading: false,
    error: null,
  });
  const requestedKey = useRef<string | null>(null);

  const load = useCallback(async () => {
    if (!catalogKey) return;
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const contents = await contentApi.catalog();
      setState({ key: catalogKey, contents, loading: false, error: null });
    } catch (reason) {
      setState({
        key: catalogKey,
        contents: [],
        loading: false,
        error:
          reason instanceof Error
            ? reason.message
            : "Не удалось загрузить содержимое приложения",
      });
    }
  }, [catalogKey]);

  useEffect(() => {
    if (!catalogKey) {
      requestedKey.current = null;
      setState({ key: null, contents: [], loading: false, error: null });
      return;
    }
    if (requestedKey.current === catalogKey) return;
    requestedKey.current = catalogKey;
    void load();
  }, [catalogKey, load]);

  // Warm the image cache for every category's card image as soon as the whole catalog is known,
  // instead of leaving each one to load for the first time only once its own page is opened.
  useEffect(() => {
    if (state.key !== catalogKey) return;
    warmImageCache(state.contents.map((content) => content.image_url));
  }, [catalogKey, state]);

  const value = useMemo<ContentCatalogState>(() => {
    const contents = state.key === catalogKey ? state.contents : [];
    return {
      contents,
      categories: contents,
      bySlug: new Map(contents.map((content) => [content.slug, content])),
      loading: Boolean(catalogKey) && (state.loading || state.key !== catalogKey),
      error: state.key === catalogKey ? state.error : null,
      reload: async () => {
        requestedKey.current = catalogKey;
        await load();
      },
    };
  }, [catalogKey, load, state]);

  return (
    <ContentCatalogContext.Provider value={value}>
      {children}
    </ContentCatalogContext.Provider>
  );
}

export function useContentCatalog(): ContentCatalogState {
  const value = useContext(ContentCatalogContext);
  if (!value) {
    throw new Error("useContentCatalog used outside ContentCatalogProvider");
  }
  return value;
}
