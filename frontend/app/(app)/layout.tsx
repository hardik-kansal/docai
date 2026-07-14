"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import type { UserProfile } from "@/lib/types";
import { PLAN_STORAGE_BYTES } from "@/lib/types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function Sidebar({
  user,
  onLogout,
  pathname,
}: {
  user: UserProfile;
  onLogout: () => void;
  pathname: string;
}) {
  const totalBytes = PLAN_STORAGE_BYTES[user.plan_type as "FREE"];
  const usedPct = Math.min((user.storage_used_bytes / totalBytes) * 100, 100);

  return (
    <nav className="sidebar">
      <div className="sidebar-logo" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="sidebar-logo-icon">🧠</div>
          <span className="sidebar-logo-text">Docai</span>
        </div>
      </div>

      {/* Nav items */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
        <Link
          href="/dashboard"
          className={`nav-item ${pathname === "/dashboard" ? "active" : ""}`}
        >
          <span className="nav-icon">📊</span>
          Dashboard
        </Link>
        <Link
          href="/documents"
          className={`nav-item ${pathname === "/documents" ? "active" : ""}`}
        >
          <span className="nav-icon">📂</span>
          Documents
        </Link>
        <Link
          href="/query"
          className={`nav-item ${pathname === "/query" ? "active" : ""}`}
        >
          <span className="nav-icon">💬</span>
          Query
        </Link>
      </div>

      {/* User + storage */}
      <div
        style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12, marginTop: 8 }}
      >
        {/* Storage bar */}
        <div className="storage-bar-wrap">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.7rem",
              color: "var(--text-muted)",
              marginBottom: 5,
            }}
          >
            <span>Storage</span>
            <span>
              {formatBytes(user.storage_used_bytes)} / {formatBytes(totalBytes)}
            </span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${usedPct}%` }} />
          </div>
        </div>

        {/* Avatar + username */}
        <div
          style={{ display: "flex", alignItems: "center", gap: 9, padding: "10px 12px" }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              background: "var(--rose-500)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "#fff",
              flexShrink: 0,
            }}
          >
            {user.username.slice(0, 2).toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="truncate" style={{ fontSize: "0.82rem", fontWeight: 600 }}>
              {user.username}
            </div>
            <div
              style={{ fontSize: "0.68rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}
            >
              {user.plan_type}
            </div>
          </div>
        </div>

        <button
          id="sidebar-logout"
          className="btn btn-ghost w-full"
          onClick={onLogout}
          style={{ fontSize: "0.8rem", justifyContent: "flex-start", gap: 9, padding: "7px 12px", marginTop: 2 }}
        >
          <span>🚪</span> Sign out
        </button>
      </div>
    </nav>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading && !user) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 14,
          background: "var(--bg-base)",
        }}
      >
        <div className="spinner spinner-lg" />
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading…</p>
      </div>
    );
  }

  if (!user) return null;

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <div className="app-shell">
      <Sidebar user={user} onLogout={handleLogout} pathname={pathname} />
      <div className="main-content">{children}</div>
    </div>
  );
}
