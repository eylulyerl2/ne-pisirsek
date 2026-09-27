import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, TOKEN_KEY, setUnauthorizedHandler, tokenStore } from "../services/api";
import { api } from "../services/endpoints";
import type { User } from "../services/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  completeLogin: (accessToken: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => tokenStore.get() !== null);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    // Başka bir sekmede giriş/çıkış yapılırsa bu sekme de senkron olsun (token tarayıcıda paylaşılır)
    function onStorage(event: StorageEvent) {
      if (event.key === TOKEN_KEY && event.newValue !== event.oldValue) logout();
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [logout]);

  useEffect(() => {
    if (!tokenStore.get()) return;
    let cancelled = false;
    api
      .me()
      .then((me) => !cancelled && setUser(me))
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) tokenStore.clear();
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const completeLogin = useCallback(
    async (accessToken: string) => {
      tokenStore.set(accessToken);
      queryClient.clear();
      setUser(await api.me());
    },
    [queryClient],
  );

  const login = useCallback(
    async (identifier: string, password: string) => {
      const { access_token } = await api.login(identifier.trim(), password);
      await completeLogin(access_token);
    },
    [completeLogin],
  );

  const register = useCallback(
    async (fullName: string, email: string, password: string) => {
      await api.register({ full_name: fullName.trim(), email: email.trim(), password });
      await login(email, password);
    },
    [login],
  );

  const value = useMemo(
    () => ({ user, loading, login, completeLogin, register, logout, setUser }),
    [user, loading, login, completeLogin, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth, AuthProvider içinde kullanılmalı");
  return context;
}
