import { createContext, ReactNode, useContext, useState } from "react";
import { api, setAuthToken, AuthUser } from "../api/client";

interface AuthCtx {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null as any);

function loadUser(): AuthUser | null {
  try { const r = localStorage.getItem("gc_user"); return r ? JSON.parse(r) : null; } catch { return null; }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("gc_token"));
  const [user, setUser] = useState<AuthUser | null>(loadUser);

  const login = async (email: string, password: string) => {
    const r = await api.login({ email, password });
    setAuthToken(r.token);
    localStorage.setItem("gc_user", JSON.stringify(r.user));
    setToken(r.token);
    setUser(r.user);
  };
  const logout = () => {
    setAuthToken(null);
    localStorage.removeItem("gc_user");
    setToken(null);
    setUser(null);
  };

  return <Ctx.Provider value={{ user, token, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
