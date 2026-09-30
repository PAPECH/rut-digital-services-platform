import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { api, getToken, setToken } from "@/api/client";
import type { ApiError } from "@/api/client";
import type { Profile } from "@/api/types";
import { getStartParam, isInsideApp, ready } from "@/max/bridge";
import { useI18n, isLang } from "@/i18n";

export interface AuthState {
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  needsRedirect: string | null;
  insideMax: boolean;
  refresh: () => Promise<void>;
  logout: () => void;
  // Task 064 -- set when the resolved identity has no active consent yet (first contact,
  // or re-contact after a completed erasure cycle) and no token/profile exists to gate on
  // `profile.consent_is_active` instead. `acceptGateConsent` re-runs the same initData
  // validation with an explicit affirmative act.
  consentRequired: boolean;
  consentPolicyUrl: string;
  consentBusy: boolean;
  consentError: string | null;
  acceptGateConsent: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);
const Ctx = AuthContext;

function readInitDataFromQuery(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get("initData") || params.get("WebAppData") || null;
}

function cleanInitDataFromUrl(): void {
  const url = new URL(window.location.href);
  let changed = false;
  for (const key of ["initData", "WebAppData", "system"]) {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  }
  if (changed) {
    // Preserve the state react-router's BrowserRouter already attached to this entry
    // (notably `idx`) -- replacing it with `{}` wipes react-router's history index,
    // which then computes as NaN forever afterward and breaks every `navigate(-1)`
    // depth check for the rest of the session (see TestPage.tsx's navigateBack).
    window.history.replaceState(window.history.state, "", url.toString());
  }
}

const WEBAPP_URL: string = import.meta.env.VITE_WEBAPP_URL || "";
const SITE_URL: string = import.meta.env.VITE_SITE_URL || "";

function isAdminStartParam(startParam: string | null | undefined): boolean {
  return startParam === "admin_login" || Boolean(startParam?.startsWith("inv_"));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsRedirect, setNeedsRedirect] = useState<string | null>(null);
  const [consentRequired, setConsentRequired] = useState(false);
  const [consentPolicyUrl, setConsentPolicyUrl] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);
  const lastInitDataRef = useRef<string | null>(null);
  const systemQuery: string | null = new URLSearchParams(
    window.location.search,
  ).get("system");
  const system: string = systemQuery || "max";
  const { setLang } = useI18n();
  const insideMax = isInsideApp();
  const triedRef = useRef(false);

  const fetchMe = useCallback(async () => {
    if (!getToken()) return false;
    try {
      const currentProfile = await api.get<Profile>("/profile");
      if (currentProfile) {
        const lang = currentProfile.language_code ?? "ru";

        if (isLang(lang)) {
          setLang(lang);
        }
        setProfile(currentProfile);
        return true;
      }
    } catch {
      // токен невалидный — продолжим попытку авторизации через initData
    }
    setToken(null);
    return false;
  }, []);

  type AuthOutcome = "ok" | "consent_required" | "error";

  const authenticateWithInitData = useCallback(
    async (initData: string, acceptConsent = false): Promise<AuthOutcome> => {
      lastInitDataRef.current = initData;
      try {
        const res = await api.post<{
          token: { access_token: string };
          user: Profile;
        }>("/auth/init-data/validate", { initData, system, acceptConsent });
        setConsentRequired(false);
        setConsentError(null);
        setToken(res.token.access_token);
        const ok = await fetchMe();
        return ok ? "ok" : "error";
      } catch (e) {
        const err = e as ApiError;
        if (err.code === "consent_required") {
          const detail = err.detail as { error?: { policy_url?: string } } | undefined;
          setConsentPolicyUrl(detail?.error?.policy_url ?? "");
          setConsentRequired(true);
          return "consent_required";
        }
        setError(err?.message ?? "Не удалось войти");
        return "error";
      }
    },
    [fetchMe],
  );

  const acceptGateConsent = useCallback(async () => {
    const initData = lastInitDataRef.current ?? window.WebApp?.initData ?? "";
    setConsentBusy(true);
    setConsentError(null);
    try {
      const outcome = await authenticateWithInitData(initData, true);
      if (outcome !== "ok") setConsentError("Не удалось подтвердить согласие");
    } finally {
      setConsentBusy(false);
    }
  }, [authenticateWithInitData]);

  useEffect(() => {
    if (triedRef.current) return;
    triedRef.current = true;
    ready();

    void (async () => {
      try {
        const startParam = getStartParam();
        if (isAdminStartParam(startParam) && SITE_URL) {
          const initData = window.WebApp?.initData ?? "";
          const target = `${SITE_URL}/login?system=${system}#initData=${encodeURIComponent(initData)}`;
          setNeedsRedirect(target);
          setLoading(false);
          return;
        }

        if (startParam === "student_login" && WEBAPP_URL) {
          const initData = window.WebApp?.initData ?? "";
          const target = new URL(WEBAPP_URL);
          target.searchParams.set("initData", initData);
          target.searchParams.set("system", system);
          window.location.replace(target.toString());
          return;
        }

        if (await fetchMe()) {
          setLoading(false);
          return;
        }

        const fromQuery = readInitDataFromQuery();
        if (fromQuery) {
          const outcome = await authenticateWithInitData(fromQuery);
          cleanInitDataFromUrl();
          if (outcome === "ok" || outcome === "consent_required") {
            setLoading(false);
            return;
          }
        }

        if (insideMax) {
          const initData = window.WebApp?.initData ?? "";
          const outcome = await authenticateWithInitData(initData);
          if (outcome === "error") setError((prev) => prev ?? "Не удалось войти");
          setLoading(false);
          return;
        }

        // 5) Standalone и нет initData — нужен явный логин.
        setLoading(false);
      } catch (e) {
        setError((e as Error)?.message ?? "Ошибка авторизации");
        setLoading(false);
      }
    })();
  }, [authenticateWithInitData, fetchMe, insideMax]);

  const logout = useCallback(() => {
    setToken(null);
    setProfile(null);
  }, [insideMax]);

  const refresh = useCallback(async () => {
    await fetchMe();
  }, [fetchMe]);

  const value = useMemo<AuthState>(
    () => ({
      profile,
      loading,
      error,
      insideMax,
      refresh,
      logout,
      needsRedirect,
      consentRequired,
      consentPolicyUrl,
      consentBusy,
      consentError,
      acceptGateConsent,
    }),
    [
      profile,
      loading,
      error,
      insideMax,
      refresh,
      logout,
      needsRedirect,
      consentRequired,
      consentPolicyUrl,
      consentBusy,
      consentError,
      acceptGateConsent,
    ],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth used outside AuthProvider");
  return v;
}
