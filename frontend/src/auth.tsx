import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getToken, getRefreshToken, request, setToken, setTokens } from "./api";
import type { TokenResponse, User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await request<User>("/api/auth/me"));
    } catch {
      // request() already rotated once; clear only if the refresh itself failed.
      if (!getRefreshToken()) setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    const token = await request<TokenResponse>("/api/auth/login", {
      method: "POST",
      form,
      token: null,
    });
    if (token.refresh_token) {
      setTokens({ access_token: token.access_token, refresh_token: token.refresh_token });
    } else {
      setToken(token.access_token);
    }
    const me = await request<User>("/api/auth/me");
    setUser(me);
    return me;
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await request<User>("/api/auth/register", {
        method: "POST",
        token: null,
        body: { email, password, full_name: fullName },
      });
      return login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setTokens(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout, refresh }),
    [user, loading, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
