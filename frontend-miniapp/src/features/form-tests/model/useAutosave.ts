import { useEffect, useRef } from "react";

const AUTOSAVE_INTERVAL_MS = 10_000;

/**
 * Periodically PATCHes whatever answers changed since the last save -- satisfies the source
 * ТЗ's "progress must survive in the MAX bot" requirement without any bot-side conversation
 * state (see Task 068). No debounce/autosave-to-server utility exists elsewhere in this repo
 * to reuse, so this mirrors `useTicketsOverview.ts`'s `setInterval` + cleanup shape (the closest
 * existing precedent for "periodically call the API while a screen is mounted").
 */
export function useAutosave(
  answers: Record<string, unknown>,
  save: (answers: Record<string, unknown>) => Promise<void>,
  enabled: boolean,
): void {
  const answersRef = useRef(answers);
  const savedRef = useRef<Record<string, unknown>>({});
  answersRef.current = answers;

  useEffect(() => {
    if (!enabled) return;

    const flush = () => {
      const current = answersRef.current;
      const changed: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(current)) {
        if (savedRef.current[key] !== value) changed[key] = value;
      }
      if (Object.keys(changed).length === 0) return;
      void save(changed).then(() => {
        savedRef.current = { ...savedRef.current, ...changed };
      });
    };

    const timer = window.setInterval(flush, AUTOSAVE_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
      flush();
    };
  }, [enabled, save]);
}
