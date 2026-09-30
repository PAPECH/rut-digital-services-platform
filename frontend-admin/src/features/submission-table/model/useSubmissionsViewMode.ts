import { useState } from "react";

export type SubmissionsViewMode = "compact" | "wide";

const VIEW_MODE_KEY = "submissions_table_view_mode";

function readStored(): SubmissionsViewMode {
  try {
    const stored = localStorage.getItem(VIEW_MODE_KEY);
    return stored === "wide" ? "wide" : "compact";
  } catch {
    return "compact";
  }
}

function writeStored(value: SubmissionsViewMode): void {
  try {
    localStorage.setItem(VIEW_MODE_KEY, value);
  } catch {
    // per-viewer convenience only -- private mode/quota failures are silently ignored
  }
}

/** Persists the admin's submissions-table display preference per browser (not tenant data, not
 * synced across devices) -- see Task 081, mirroring form_tests' useAttemptsDisplayPrefs. */
export function useSubmissionsViewMode() {
  const [viewMode, setViewModeState] = useState<SubmissionsViewMode>(readStored);

  const setViewMode = (mode: SubmissionsViewMode) => {
    setViewModeState(mode);
    writeStored(mode);
  };

  return { viewMode, setViewMode };
}
