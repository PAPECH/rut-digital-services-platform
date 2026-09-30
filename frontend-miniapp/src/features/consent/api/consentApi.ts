import { api } from "@/api/client";

export interface ConsentStatus {
  is_active: boolean;
  given_at: string | null;
  revoked_at: string | null;
  deletion_due_at: string | null;
  deleted_at: string | null;
  policy_version: string | null;
  policy_url: string;
}

// Re-accept while a session still exists (the 10-business-day grace window after revoke --
// the User row and JWT are both still valid at that point). The *first* accept, and accept
// after a completed erasure cycle, go through AuthProvider's initData re-validation
// instead -- see docs/tasks/064, "no session to reuse in either case".
export function acceptConsent(): Promise<ConsentStatus> {
  return api.post<ConsentStatus>("/consent/accept");
}

export function revokeConsent(): Promise<ConsentStatus> {
  return api.post<ConsentStatus>("/consent/revoke");
}

interface ConsentNoticeOut {
  key: string;
  value: string | null;
}

// Public read (no session needed -- same trust level as GET /manifest, see the backend
// router's comment): admin-authored HTML notice text shown at the consent gate, mirrors
// what the bot reads via the same endpoint. Returns null (not a 404) when the platform
// admin hasn't set one yet, so the caller can fall back to its own default text.
export function getConsentNotice(lang: "ru" | "en"): Promise<string | null> {
  return api.get<ConsentNoticeOut>(`/consent/notice/${lang}`).then((r) => r.value);
}

interface PolicyDocumentContentOut {
  value: string | null;
}

// Public read of the raw policy-document HTML (no page shell -- that variant is
// GET /consent/policy-document, meant for a standalone browser tab), for PolicyScreen to
// embed in-app. Returns null when the platform admin hasn't filled it in yet.
export function getPolicyDocument(): Promise<string | null> {
  return api.get<PolicyDocumentContentOut>("/consent/policy-document/content").then((r) => r.value);
}
