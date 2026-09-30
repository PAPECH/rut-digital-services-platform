import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { getBotSlug } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import type { PublishedContent } from "@/entities/content/model/types";
import { contentApi } from "@/features/content/api/contentApi";
import { warmImageCache } from "@/lib/imageCache";

interface HomeContentState {
  content: PublishedContent | null;
  loading: boolean;
  error: string | null;
}

interface HomeLoadState {
  key: string | null;
  content: PublishedContent | null;
  loading: boolean;
  error: string | null;
}

const HomeContentContext = createContext<HomeContentState | null>(null);

/**
 * Mounted once above the router (see main.tsx) so the home screen's published content survives
 * route changes -- `HomePage` used to fetch it in a component-local effect, which meant every
 * "back" navigation to "/" unmounted/remounted the page and re-fetched (and re-showed a loading
 * skeleton for) content that hadn't changed since the app opened.
 */
export function HomeContentProvider({ children }: { children: React.ReactNode }) {
  const { profile } = useAuth();
  const homeKey = profile ? `${getBotSlug()}:${profile.id}` : null;
  const [state, setState] = useState<HomeLoadState>({
    key: null,
    content: null,
    loading: false,
    error: null,
  });
  const requestedKey = useRef<string | null>(null);

  const load = useCallback(async () => {
    if (!homeKey) return;
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const content = await contentApi.home();
      setState({ key: homeKey, content, loading: false, error: null });
    } catch (reason) {
      setState({
        key: homeKey,
        content: null,
        loading: false,
        error: reason instanceof Error ? reason.message : "Не удалось загрузить главный экран",
      });
    }
  }, [homeKey]);

  useEffect(() => {
    if (!homeKey) {
      requestedKey.current = null;
      setState({ key: null, content: null, loading: false, error: null });
      return;
    }
    if (requestedKey.current === homeKey) return;
    requestedKey.current = homeKey;
    void load();
  }, [homeKey, load]);

  // The home category is excluded from ContentCatalogProvider's catalog (it's fetched via its
  // own dedicated endpoint), so its own hero image needs its own preload trigger here.
  useEffect(() => {
    if (state.key !== homeKey || !state.content) return;
    warmImageCache([state.content.image_url]);
  }, [homeKey, state]);

  const value = useMemo<HomeContentState>(
    () => ({
      content: state.key === homeKey ? state.content : null,
      loading: Boolean(homeKey) && (state.loading || state.key !== homeKey),
      error: state.key === homeKey ? state.error : null,
    }),
    [homeKey, state],
  );

  return <HomeContentContext.Provider value={value}>{children}</HomeContentContext.Provider>;
}

export function useHomeContent(): HomeContentState {
  const value = useContext(HomeContentContext);
  if (!value) {
    throw new Error("useHomeContent used outside HomeContentProvider");
  }
  return value;
}
