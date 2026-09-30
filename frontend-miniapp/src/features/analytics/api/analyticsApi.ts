import { api } from "@/api/client";
import type { AnalyticsEvent } from "@/features/analytics/model/types";
import {
  createAnalyticsEventId,
  getAnalyticsSessionId,
} from "@/features/analytics/model/session";

const emittedOnce = new Set<string>();

let analyticsSuppressed = false;

/** Preview mode has no real end user — nothing it does should count as product analytics. */
export function setAnalyticsSuppressed(suppressed: boolean): void {
  analyticsSuppressed = suppressed;
}

export function isAnalyticsSuppressed(): boolean {
  return analyticsSuppressed;
}

export async function trackAnalyticsEvent(event: AnalyticsEvent): Promise<void> {
  if (analyticsSuppressed) return;
  await api.post<void>("/analytics/events", {
    ...event,
    event_id: createAnalyticsEventId(),
    session_id: getAnalyticsSessionId(),
  });
}

export function trackAnalyticsEventInBackground(event: AnalyticsEvent): void {
  void trackAnalyticsEvent(event).catch(() => undefined);
}

export function trackAnalyticsEventOnce(key: string, event: AnalyticsEvent): void {
  if (emittedOnce.has(key)) return;
  emittedOnce.add(key);
  trackAnalyticsEventInBackground(event);
}
