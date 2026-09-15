import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError, clearToken, getToken, setToken } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_EXPIRED_NOTICE_KEY = "rainbow_session_expired_notice";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function loadUser() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      setLoading(true); setConnectionError(false);
      try {
        const current = await api.me<User>();
        if (!cancelled) setUser(current);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) clearToken();
        else setConnectionError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadUser();
    const reconnect = () => setRetry(value => value + 1);
    window.addEventListener("online", reconnect);
    return () => { cancelled = true; window.removeEventListener("online", reconnect); };
  }, [retry]);

  useEffect(() => {
    const handleUnauthorized = () => {
      window.sessionStorage.setItem(SESSION_EXPIRED_NOTICE_KEY, "Your session has expired. Please sign in again.");
      setUser(null);
    };
    window.addEventListener("rainbow:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("rainbow:unauthorized", handleUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(email: string, password: string) {
        const response = await api.login(email, password);
        setToken(response.access_token);
        setUser(response.user); setConnectionError(false);
      },
      logout() {
        void api.logout().catch(() => undefined);
        clearToken();
        setUser(null);
      }
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{connectionError && !user ? <main className="mx-auto my-12 max-w-lg space-y-4 rounded-xl border bg-white p-6"><h1 className="text-2xl font-bold">Connection interrupted</h1><p>Your saved drafts and sign-in are still on this device. Reconnect and try again.</p><button className="min-h-12 rounded-lg bg-teal-700 px-5 font-semibold text-white" onClick={() => setRetry(value => value + 1)}>Try again</button></main> : children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
