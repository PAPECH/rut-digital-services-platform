import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  api,
  logoutAdminSession,
  refreshAdminSession,
  setToken,
} from "@/api/client";
import type { AdminProfile } from "@/api/types";

interface AuthState {
  admin: AdminProfile | null;
  loading: boolean;
  loginWithInitData: (
    init_data: string,
    system: "max" | "beavers",
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<AdminProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const restoreSession = useCallback(async () => {
    try {
      const session = await refreshAdminSession();
      setAdmin(session.admin);
    } catch {
      setToken(null);
      setAdmin(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  const loginWithInitData = useCallback(
    async (init_data: string, system: "max" | "beavers") => {
      const res = await api.post<{
        token: { access_token: string };
        admin: AdminProfile;
      }>("/auth/admin/login", { initData: init_data, system });
      setToken(res.token.access_token);
      setAdmin(res.admin);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await logoutAdminSession();
    } finally {
      setAdmin(null);
    }
  }, []);

  const value = useMemo(
    () => ({ admin, loading, loginWithInitData, logout }),
    [admin, loading, loginWithInitData, logout],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(AuthCtx);
  if (!v) throw new Error("useAuth must be used within AuthProvider");
  return v;
}
