import { useState } from "react";

export type AttemptsViewMode = "table" | "drawer";
export type AttemptsValueMode = "text" | "score";

const VIEW_MODE_KEY = "form_tests_attempts_view_mode";
const VALUE_MODE_KEY = "form_tests_attempts_value_mode";

function readStored<T extends string>(key: string, fallback: T, allowed: readonly T[]): T {
  try {
    const stored = localStorage.getItem(key);
    return stored && (allowed as readonly string[]).includes(stored) ? (stored as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeStored(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // per-viewer convenience only -- private mode/quota failures are silently ignored
  }
}

/** Persists the admin's results-view display preference per browser (not tenant data, not
 * synced across devices) -- see Task 077. */
export function useAttemptsDisplayPrefs() {
  const [viewMode, setViewModeState] = useState<AttemptsViewMode>(() =>
    readStored(VIEW_MODE_KEY, "drawer", ["table", "drawer"] as const),
  );
  const [valueMode, setValueModeState] = useState<AttemptsValueMode>(() =>
    readStored(VALUE_MODE_KEY, "text", ["text", "score"] as const),
  );

  const setViewMode = (mode: AttemptsViewMode) => {
    setViewModeState(mode);
    writeStored(VIEW_MODE_KEY, mode);
  };

  const setValueMode = (mode: AttemptsValueMode) => {
    setValueModeState(mode);
    writeStored(VALUE_MODE_KEY, mode);
  };

  return { viewMode, setViewMode, valueMode, setValueMode };
}
