"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useDocuments } from "@/hooks/useDocuments";
import { PLAN_STORAGE_BYTES } from "@/lib/types";
import type { DocumentStatus, DocumentResponse } from "@/lib/types";
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
function StatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { cls: string; label: string; dot: string }> = {
    pending: { cls: "badge-pending", label: "Pending", dot: "🕐" },
    processing: { cls: "badge-processing", label: "Processing", dot: "⚙️" },
    pending_embedding: { cls: "badge-processing", label: "Embedding", dot: "🔄" },
    ready: { cls: "badge-ready", label: "Ready", dot: "✓" },
    error: { cls: "badge-error", label: "Error", dot: "✕" },
  };
  const conf = map[status] ?? map.pending;
  return (
    <span className={`badge ${conf.cls}`}>
      {conf.dot} {conf.label}
    </span>
  );
}
function StatCard({
  icon,
  iconBg,
  value,
  label,
}: {
  icon: string;
  iconBg: string;
  value: string;
  label: string;
}) {
  return (
    <div className="card stat-card animate-fade-up">
      <div className="stat-icon" style={{ background: iconBg }}>
        {icon}
      </div>
      <div className="stat-value gradient-text">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
export default function DashboardPage() {
  const { user, refetch } = useAuth();
  const { documents, loading: docsLoading } = useDocuments();
  const router = useRouter();


  useEffect(() => {
    // Refetch user stats to ensure storage used is up to date when documents change
    refetch();
  }, [documents.length, refetch]);

  if (!user) return null;
  const totalBytes = 2 * 1024 * 1024 * 1024; // 2GB
  const usedPct = ((user.storage_used_bytes / totalBytes) * 100).toFixed(3);
  const recentDocs = documents.slice(0, 5);
  const stats = [
    {
      icon: "📄",
      iconBg: "rgba(139,92,246,0.15)",
      value: String(documents.length),
      label: "Total Documents",
    },
    {
      icon: "💾",
      iconBg: "rgba(6,182,212,0.12)",
      value: `${formatBytes(user.storage_used_bytes)} (${usedPct}%)`,
      label: "Storage 2GB",
    },
  ];
  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ marginBottom: 4 }}>
              {" "}
              <span className="gradient-text">{user.username}</span>
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Here&apos;s your document intelligence overview
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Link href="/documents" className="btn btn-secondary btn-sm">
              📄 Upload Document
            </Link>
            <Link href="/query" className="btn btn-primary btn-sm">
              💬 Ask a Question
            </Link>
          </div>
        </div>
      </div>
      <div className="page-content">
        {/* Stats */}
        <div className="stats-grid stagger-children">
          {stats.map((s) => (
            <StatCard key={s.label + s.value} {...s} />
          ))}
        </div>
        {/* Recent Documents */}
        <div className="card" style={{ padding: "24px", marginBottom: 24 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 20,
            }}
          >
            <h3>Recent Documents</h3>
            <Link
              href="/documents"
              className="btn btn-ghost btn-sm"
              style={{ fontSize: "0.8rem" }}
            >
              View all →
            </Link>
          </div>
          {docsLoading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="skeleton"
                  style={{ height: 56, borderRadius: "var(--radius-md)" }}
                />
              ))}
            </div>
          ) : recentDocs.length === 0 ? (
            <div className="empty-state" style={{ padding: "40px 24px" }}>
              <div className="empty-icon">📄</div>
              <p style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
                No documents yet
              </p>
              <Link href="/documents" className="btn btn-primary btn-sm">
                Upload your first document
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {recentDocs.map((doc: DocumentResponse) => (
                <div
                  key={doc.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    padding: "12px 16px",
                    background: "var(--bg-card)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    transition: "all var(--transition-fast)",
                    cursor: "default",
                  }}
                  className="animate-fade-up"
                >
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      background: "rgba(139,92,246,0.12)",
                      borderRadius: "var(--radius-sm)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "1.1rem",
                      flexShrink: 0,
                    }}
                  >
                    📄
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      className="truncate"
                      style={{ fontSize: "0.875rem", fontWeight: 600 }}
                    >
                      {doc.filename}
                    </div>
                    <div
                      style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}
                    >
                      {formatDate(doc.created_at)}
                    </div>
                  </div>
                  <StatusBadge status={doc.status} />
                  {doc.status === "ready" && (
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() =>
                        router.push(
                          `/query?doc=${encodeURIComponent(doc.id)}`
                        )
                      }
                      title="Query this document"
                    >
                      💬
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        {/* Quick start card */}
        <div
          className="card card-elevated"
          style={{
            padding: "28px",
            background:
              "linear-gradient(135deg, rgba(124,58,237,0.12) 0%, rgba(6,182,212,0.06) 100%)",
            borderColor: "rgba(139,92,246,0.2)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 24,
              flexWrap: "wrap",
            }}
          >
            <div style={{ flex: 1, minWidth: 200 }}>
              <h3 style={{ marginBottom: 8 }}>
                Ready to explore your documents?
              </h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: 0 }}>
                Ask questions in natural language and get grounded answers with citations.
              </p>
            </div>
            <Link href="/query" className="btn btn-primary">
              💬 Open Query Interface
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}