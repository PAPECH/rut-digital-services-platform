import { useMemo } from "react";

import type { Profile } from "@/api/types";
import { AuthContext, type AuthState } from "@/auth/AuthProvider";

/**
 * Drop-in substitute for `AuthProvider` inside the admin content-builder preview iframe
 * (`/preview/:token`). There is no real MAX login there, so this never calls the backend —
 * it just satisfies every `useAuth()` consumer's gating on a truthy `profile` with a synthetic
 * placeholder. The real authorization for preview reads comes from the short-lived,
 * bot-scoped access token the backend issues alongside the preview content
 * (`DraftPreviewResponse.preview_access_token`), not from this profile.
 */
const PREVIEW_PROFILE: Profile = {
  id: 0,
  user_id: "preview",
  system: "max",
  first_name: "Предпросмотр",
  last_name: null,
  patronymic: null,
  username: null,
  phone: null,
  phone_verified: false,
  email: null,
  photo_url: null,
  language_code: "ru",
  birth_date: null,
  study_group: null,
  rut_personnel_number: null,
  job_title: null,
  structural_unit: null,
  shared_data: {},
  local_data: {},
  ban_chat: false,
  ban_chat_reason: null,
  ban_forms: false,
  ban_forms_reason: null,
  ban_app: false,
  ban_app_reason: null,
  consent_is_active: true,
  consent_given_at: null,
  consent_revoked_at: null,
  consent_deletion_due_at: null,
  consent_policy_url: "",
};

export function PreviewAuthProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo<AuthState>(
    () => ({
      profile: PREVIEW_PROFILE,
      loading: false,
      error: null,
      needsRedirect: null,
      insideMax: false,
      refresh: async () => undefined,
      logout: () => undefined,
      consentRequired: false,
      consentPolicyUrl: "",
      consentBusy: false,
      consentError: null,
      acceptGateConsent: async () => undefined,
    }),
    [],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
