"use client";
import { useState, FormEvent, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { loginWithGoogle, user, loading, error } = useAuth();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  async function handleGoogleSignIn() {
    setSubmitting(true);
    try {
      await loginWithGoogle();
    } catch {
      setSubmitting(false);
    }
  }

  const displayError = error;

  return (
    <main className="auth-page">
      <section className="auth-hero">
        {/* ── Left brand panel ── */}
        <div className="auth-hero-brand">
          <div style={{ position: "relative", zIndex: 1, textAlign: "center", width: "100%", maxWidth: 650, margin: "0 auto" }}>
            <h1 style={{ marginBottom: 12, color: "#ffffff", fontSize: "3rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
              Docai
            </h1>
            <p style={{ color: "#dddddd", lineHeight: 1.75, fontSize: "1.1rem", marginBottom: 40, fontWeight: 500 }}>
              Intelligent Document Processing Pipeline
            </p>
          </div>
        </div>

        {/* ── Right WIDER form panel ── */}
        <div className="auth-hero-form">
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

            <form className="auth-form" id="login-form">
              {displayError && (
                <div className="alert alert-error animate-fade-in">
                  <span>⚠️</span><span>{displayError}</span>
                </div>
              )}

              <button
                id="login-submit"
                type="button"
                onClick={handleGoogleSignIn}
                className="btn btn-primary btn-lg w-full"
                disabled={submitting || loading}
                style={{ 
                  marginTop: 4, 
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center", 
                  gap: 12,
                  background: "white",
                  color: "#333",
                  border: "1px solid #ddd"
                }}
              >
                {submitting ? (
                  <><div className="spinner spinner-sm" style={{ borderTopColor: "#333" }} /> Redirecting…</>
                ) : (
                  <>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    Continue with Google
                  </>
                )}
              </button>
            </form>
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
          <span className="auth-footer-highlight">Frontend</span> crafted with <span className="auth-footer-highlight">Agentic AI</span> ⚡<br />
          <span className="auth-footer-highlight">Backend</span> built entirely from scratch by developer (without AI) 💻
        </p>
      </footer>
    </main>
  );
}
