import { useCallback, useEffect, useRef, useState } from "react";

import { api, getBotSlug, getToken } from "@/api/client";
import type { Submission } from "@/api/types";

export function useUserSubmissions() {
  const [items, setItems] = useState<Submission[]>([]);
  const [selected, setSelected] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const url = new URL(
      `${import.meta.env.VITE_API_URL}/api/ws/chat`,
      window.location.origin,
    );
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.searchParams.set("token", token);
    url.searchParams.set("bot_slug", getBotSlug());
    const ws = new WebSocket(url.toString());
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as {
          type?: string;
          data?: Submission;
        };
        if (message.type !== "submission_updated" || !message.data) return;
        const updated = message.data;
        setItems((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
        setSelected((current) =>
          current?.id === updated.id ? updated : current,
        );
      } catch {
        // Ignore unrelated or malformed websocket messages.
      }
    };
    return () => {
      wsRef.current = null;
      ws.close();
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    void api
      .get<Submission[]>("/submissions")
      .then((submissions) => {
        if (mounted) setItems(submissions);
      })
      .catch((loadError: unknown) => {
        if (mounted)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Не удалось загрузить заявки",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const open = useCallback(async (submission: Submission) => {
    setError(null);
    try {
      setSelected(await api.get<Submission>(`/submissions/${submission.id}`));
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Не удалось открыть заявку",
      );
    }
  }, []);

  return {
    items,
    selected,
    loading,
    error,
    open,
    close: () => setSelected(null),
  };
}
