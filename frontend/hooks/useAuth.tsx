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
  login: (username: string, pwd: string) => Promise<void>;
  signup: (username: string, pwd: string) => Promise<void>;
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

  const login = useCallback(
    async (username: string, pwd: string): Promise<void> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        await authApi.login({ username, pwd });
        await fetchMe();
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : "Login failed";
        setState((s) => ({ ...s, loading: false, error: msg }));
        throw err;
      }
    },
    [fetchMe]
  );

  const signup = useCallback(
    async (username: string, pwd: string): Promise<void> => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        await authApi.signup({ username, pwd });
        await authApi.login({ username, pwd });
        await fetchMe();
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : "Signup failed";
        setState((s) => ({ ...s, loading: false, error: msg }));
        throw err;
      }
    },
    [fetchMe]
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
    login,
    signup,
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
