import { api } from "@/api/client";
import { isAnalyticsSuppressed } from "@/features/analytics/api/analyticsApi";

const reportedOnce = new Set<string>();

/**
 * Reports a `target: webapp` campaign-link open (Task 026) — separate from and in addition to
 * the `app_open` analytics event; the backend resolves the caller's own already-established
 * membership from the session, no payload needed here.
 */
export function reportCampaignLinkOpenOnce(code: string): void {
  if (isAnalyticsSuppressed()) return; // preview session, not a real member
  if (reportedOnce.has(code)) return;
  reportedOnce.add(code);
  void api
    .post<void>(`/campaign-links/${encodeURIComponent(code)}/open`)
    .catch(() => undefined);
}
