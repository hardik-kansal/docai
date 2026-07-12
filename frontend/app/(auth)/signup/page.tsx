"use client";
import { useState, FormEvent, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function SignupPage() {
  const { signup, user, loading, error } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [pwd, setPwd] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/query");
  }, [user, loading, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFieldError(null);
    if (!username.trim() || !pwd.trim()) { setFieldError("All fields are required."); return; }
    if (username.length < 1 || username.length > 10) { setFieldError("Username must be 1–10 characters."); return; }
    if (pwd.length < 1 || pwd.length > 10) { setFieldError("Password must be 1–10 characters."); return; }
    if (pwd !== confirm) { setFieldError("Passwords do not match."); return; }
    setSubmitting(true);
    try {
      await signup(username, pwd);
      setSuccess(true);
      setTimeout(() => router.replace("/query"), 800);
    } catch {
      // error from hook
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
          {/* Folder icon */}
          <div style={{ position: "relative", width: 100, height: 84, margin: "0 auto 32px" }}>
            <div style={{ position: "absolute", top: 0, left: 0, width: 52, height: 22, background: "var(--rose-500)", borderRadius: "8px 10px 0 0" }} />
            <div style={{
              position: "absolute", bottom: 0, left: 0, right: 0, height: 68,
              background: "var(--rose-400)",
              borderRadius: "0 10px 10px 10px",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 6px 20px rgba(201,75,107,0.35)",
            }}>
              <span style={{ fontSize: "1.8rem" }}>✨</span>
            </div>
          </div>

          <h1 style={{ marginBottom: 12 }}>
            <span className="gradient-text">Get started free</span>
          </h1>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.75, fontSize: "0.95rem", marginBottom: 32 }}>
            Upload documents and unlock AI-powered Q&A with grounded citations.
          </p>

          {/* Plan features */}
          <div style={{
            padding: "20px 18px",
            background: "rgba(255,255,255,0.7)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--border-subtle)",
            textAlign: "left",
          }}>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 12 }}>
              Free Plan Includes
            </div>
            {["2 GB document storage", "Unlimited queries", "Hybrid semantic search", "Citation grounding", "Confidence scoring"].map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--status-ready)", fontSize: "0.7rem" }}>✓</span>
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right WIDER form panel ── */}
      <div className="auth-form-panel">
        <div style={{ maxWidth: 480, width: "100%" }}>
          <div style={{ marginBottom: 36 }}>
            <div style={{
              width: 44, height: 44,
              background: "var(--rose-500)",
              borderRadius: "var(--radius-lg)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1.3rem", marginBottom: 22,
              boxShadow: "var(--shadow-accent)",
            }}>
              🧑‍💻
            </div>
            <h2 style={{ marginBottom: 6 }}>Create your account</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              Start analysing your documents in seconds
            </p>
          </div>

          {success ? (
            <div className="alert alert-success animate-fade-in" style={{ flexDirection: "column", gap: 8, padding: "24px", justifyContent: "center", alignItems: "center" }}>
              <div style={{ fontSize: "2rem" }}>🎉</div>
              <div style={{ fontWeight: 600 }}>Account created! Redirecting…</div>
            </div>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit} id="signup-form">
              {displayError && (
                <div className="alert alert-error animate-fade-in">
                  <span>⚠️</span><span>{displayError}</span>
                </div>
              )}

              <div className="input-group">
                <label className="input-label" htmlFor="signup-username">
                  Username <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(max 10 chars)</span>
                </label>
                <input
                  id="signup-username"
                  className={`input ${displayError ? "input-error" : ""}`}
                  type="text"
                  placeholder="Choose a username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  maxLength={10}
                  autoComplete="username"
                  autoFocus
                  disabled={submitting}
                />
              </div>

              <div className="input-group">
                <label className="input-label" htmlFor="signup-pwd">
                  Password <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(max 10 chars)</span>
                </label>
                <input
                  id="signup-pwd"
                  className={`input ${displayError ? "input-error" : ""}`}
                  type="password"
                  placeholder="Choose a password"
                  value={pwd}
                  onChange={(e) => setPwd(e.target.value)}
                  maxLength={10}
                  autoComplete="new-password"
                  disabled={submitting}
                />
              </div>

              <div className="input-group">
                <label className="input-label" htmlFor="signup-confirm">Confirm password</label>
                <input
                  id="signup-confirm"
                  className={`input ${pwd !== confirm && confirm ? "input-error" : ""}`}
                  type="password"
                  placeholder="Repeat your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  maxLength={10}
                  autoComplete="new-password"
                  disabled={submitting}
                />
                {pwd !== confirm && confirm && (
                  <span className="input-error-text">Passwords do not match</span>
                )}
              </div>

              <button
                id="signup-submit"
                type="submit"
                className="btn btn-primary btn-lg w-full"
                disabled={submitting || loading}
                style={{ marginTop: 4 }}
              >
                {submitting ? (
                  <><div className="spinner spinner-sm" style={{ borderTopColor: "white" }} /> Creating account…</>
                ) : "Create Account →"}
              </button>

              <p style={{ textAlign: "center", fontSize: "0.875rem", color: "var(--text-muted)" }}>
                Already have an account?{" "}
                <Link href="/login" style={{ color: "var(--rose-600)", fontWeight: 600 }}>
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
