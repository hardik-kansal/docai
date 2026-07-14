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
      <section className="auth-hero">
        {/* ── Left brand panel ── */}
        <div className="auth-hero-brand">
          <div style={{ position: "relative", zIndex: 1, textAlign: "center", width: "100%", maxWidth: 650, margin: "0 auto" }}>
            <h1 style={{ marginBottom: 12, color: "#ffffff", fontSize: "3rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
              Nexus AI
            </h1>
            <p style={{ color: "#dddddd", lineHeight: 1.75, fontSize: "1.1rem", marginBottom: 40, fontWeight: 500 }}>
              Intelligent Document Processing Pipeline
            </p>
          </div>
        </div>

        {/* ── Right WIDER form panel ── */}
        <div className="auth-hero-form">
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
      </section>

      <section className="auth-diagram-section">
        <h2 className="diagram-title">System Architecture</h2>
        <p className="diagram-subtitle">
          A high-level overview of our scalable data ingestion and processing pipeline.
        </p>
        <img src="/bg.png" alt="Architecture Diagram" className="arch-diagram" />
      </section>

      <footer className="auth-footer">
        <div className="auth-footer-socials">
          <a href="https://instagram.com" target="_blank" rel="noreferrer">📷 Instagram</a>
          <a href="https://github.com" target="_blank" rel="noreferrer">🐙 GitHub</a>
          <a href="https://linkedin.com" target="_blank" rel="noreferrer">💼 LinkedIn</a>
        </div>
        <p className="auth-footer-text">
          <span className="auth-footer-highlight">Frontend</span> crafted with <span className="auth-footer-highlight">Agentic AI</span> ⚡<br/>
          <span className="auth-footer-highlight">Backend</span> built entirely from scratch by developer (without AI) 💻
        </p>
      </footer>
    </main>
  );
}
