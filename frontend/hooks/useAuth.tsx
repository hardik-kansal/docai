"use client";
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authApi, ApiError } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

interface AuthState {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
}

interface AuthContextType extends AuthState {
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  refetch: () => Promise<void>;
  updateUser: (updates: Partial<UserProfile>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });

  const fetchMe = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const user = await authApi.me();
      setState({ user, loading: false, error: null });
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setState({ user: null, loading: false, error: null });
      } else {
        setState({ user: null, loading: false, error: "Failed to load profile" });
      }
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const updateUser = useCallback((updates: Partial<UserProfile>) => {
    setState((s) => ({
      ...s,
      user: s.user ? { ...s.user, ...updates } : null,
    }));
  }, []);

  const loginWithGoogle = useCallback(
    async (): Promise<void> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const res = await authApi.getGoogleAuthUrl();
        window.location.href = res.url;
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : "Failed to get auth URL";
        setState((s) => ({ ...s, loading: false, error: msg }));
        throw err;
      }
    },
    []
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout();
    } catch {
      // best-effort
    }
    setState({ user: null, loading: false, error: null });
  }, []);

  const value = {
    ...state,
    loginWithGoogle,
    logout,
    refetch: fetchMe,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
