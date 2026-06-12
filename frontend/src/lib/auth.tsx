"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { apiFetch, login as apiLogin, logout as apiLogout, tokenStore } from "./api";

export type Role =
  | "MASTER_ADMIN"
  | "SUPER_ADMIN"
  | "COMPANY_ADMIN"
  | "HR_ADMIN"
  | "PROCUREMENT_ADMIN"
  | "FINANCE_ADMIN";

export interface CurrentUser {
  id: string;
  email: string;
  role: Role;
  tenant: string | null;
  is_master_admin: boolean;
}

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    if (!tokenStore.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await apiFetch<CurrentUser>("/auth/me/"));
    } catch {
      apiLogout();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  async function signIn(email: string, password: string) {
    await apiLogin(email, password);
    setLoading(true);
    await loadMe();
  }

  function signOut() {
    apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
