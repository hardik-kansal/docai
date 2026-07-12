"use client";
import { useState, FormEvent, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login, user, loading, error } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [pwd, setPwd] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) router.replace("/query");
  }, [user, loading, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !pwd.trim()) {
      setFieldError("Both fields are required.");
      return;
    }
    setFieldError(null);
    setSubmitting(true);
    try {
      await login(username, pwd);
      router.replace("/query");
    } catch {
      // error shown via hook
    } finally {
      setSubmitting(false);
    }
  }

  const displayError = fieldError ?? error;

  return (
    <main className="auth-page">
      {/* ── Left brand panel ── */}
      <div className="auth-brand">
        <div style={{ position: "relative", zIndex: 1, textAlign: "center", maxWidth: 340 }}>
          {/* Folder icon inspired logo */}
          <div style={{ position: "relative", width: 100, height: 84, margin: "0 auto 32px" }}>
            {/* folder tab */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: 52,
                height: 22,
                background: "var(--rose-500)",
                borderRadius: "8px 10px 0 0",
              }}
            />
            {/* folder body */}
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: 68,
                background: "var(--rose-400)",
                borderRadius: "0 10px 10px 10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 6px 20px rgba(201,75,107,0.35)",
              }}
            >
              <span style={{ fontSize: "1.8rem" }}>🧠</span>
            </div>
          </div>

          <h1 style={{ marginBottom: 12 }}>
            <span className="gradient-text">Nexus AI</span>
          </h1>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.75, fontSize: "0.95rem", marginBottom: 36 }}>
            Ask questions about your documents and get grounded answers with citations.
          </p>

          {/* Feature list */}
          {[
            { icon: "🔍", label: "Hybrid semantic search" },
            { icon: "📌", label: "Citation-level grounding" },
            { icon: "⚡", label: "Streaming answers" },
            { icon: "🛡️", label: "PII redaction & guardrails" },
          ].map((f) => (
            <div
              key={f.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                background: "rgba(255,255,255,0.7)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                textAlign: "left",
                marginBottom: 8,
              }}
            >
              <span>{f.icon}</span>
              <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)", fontWeight: 500 }}>{f.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right WIDER form panel ── */}
      <div className="auth-form-panel">
        <div style={{ maxWidth: 480, width: "100%" }}>
          <div style={{ marginBottom: 40 }}>
            <div
              style={{
                width: 44,
                height: 44,
                background: "var(--rose-500)",
                borderRadius: "var(--radius-lg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.3rem",
                marginBottom: 22,
                boxShadow: "var(--shadow-accent)",
              }}
            >
              🔑
            </div>
            <h2 style={{ marginBottom: 6 }}>Welcome back</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              Sign in to your account to continue
            </p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} id="login-form">
            {displayError && (
              <div className="alert alert-error animate-fade-in">
                <span>⚠️</span><span>{displayError}</span>
              </div>
            )}

            <div className="input-group">
              <label className="input-label" htmlFor="login-username">Username</label>
              <input
                id="login-username"
                className={`input ${displayError ? "input-error" : ""}`}
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                maxLength={10}
                autoComplete="username"
                autoFocus
                disabled={submitting}
              />
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="login-pwd">Password</label>
              <input
                id="login-pwd"
                className={`input ${displayError ? "input-error" : ""}`}
                type="password"
                placeholder="Enter your password"
                value={pwd}
                onChange={(e) => setPwd(e.target.value)}
                maxLength={10}
                autoComplete="current-password"
                disabled={submitting}
              />
            </div>

            <button
              id="login-submit"
              type="submit"
              className="btn btn-primary btn-lg w-full"
              disabled={submitting || loading}
              style={{ marginTop: 4 }}
            >
              {submitting ? (
                <><div className="spinner spinner-sm" style={{ borderTopColor: "white" }} /> Signing in…</>
              ) : "Sign In →"}
            </button>

            <p style={{ textAlign: "center", fontSize: "0.875rem", color: "var(--text-muted)" }}>
              Don&apos;t have an account?{" "}
              <Link href="/signup" style={{ color: "var(--rose-600)", fontWeight: 600 }}>
                Create one
              </Link>
            </p>
          </form>
        </div>
      </div>
    </main>
  );
}
