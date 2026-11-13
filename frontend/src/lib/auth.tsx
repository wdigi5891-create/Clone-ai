"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; name: string; accept_terms: boolean }) => Promise<void>;
  logout: () => void;
}
const Ctx = createContext<AuthState>(null as unknown as AuthState);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    api<User>("/api/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
    const onLogout = () => setUser(null);
    window.addEventListener("avc-logout", onLogout);
    return () => window.removeEventListener("avc-logout", onLogout);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ token: string; user: User }>("/api/auth/login", { body: { email, password } });
    setToken(r.token);
    setUser(r.user);
  }, []);
  const register = useCallback(async (data: { email: string; password: string; name: string; accept_terms: boolean }) => {
    const r = await api<{ token: string; user: User }>("/api/auth/register", { body: data });
    setToken(r.token);
    setUser(r.user);
  }, []);
  const logout = useCallback(() => { setToken(null); setUser(null); }, []);

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}
