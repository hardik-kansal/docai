"use client";
import { useCallback, useRef, useState } from "react";
import { useDocuments } from "@/hooks/useDocuments";
import type { DocumentResponse, DocumentStatus } from "@/lib/types";
import { useRouter } from "next/navigation";
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
function StatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { cls: string; label: string }> = {
    pending: { cls: "badge-pending", label: "⏳ Pending" },
    processing: { cls: "badge-processing", label: "⚙️ Processing" },
    pending_embedding: { cls: "badge-processing", label: "🔄 Embedding" },
    ready: { cls: "badge-ready", label: "✅ Ready" },
    error: { cls: "badge-error", label: "❌ Error" },
  };
  const conf = map[status] ?? map.pending;
  return <span className={`badge ${conf.cls}`}>{conf.label}</span>;
}
function UploadZone({
  onUpload,
  uploading,
}: {
  onUpload: (file: File) => void;
  uploading: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
      e.target.value = "";
    },
    [onUpload]
  );
  return (
    <div
      id="upload-zone"
      className={`drop-zone ${dragging ? "drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      style={{ opacity: uploading ? 0.6 : 1, cursor: uploading ? "not-allowed" : "pointer" }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.docx,.md"
        style={{ display: "none" }}
        onChange={handleChange}
        disabled={uploading}
        id="file-input"
      />
      <div
        style={{
          width: 64,
          height: 64,
          background: "rgba(139,92,246,0.12)",
          borderRadius: "var(--radius-xl)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "2rem",
          margin: "0 auto 20px",
          transition: "all var(--transition-base)",
          boxShadow: dragging ? "0 0 30px rgba(139,92,246,0.25)" : "none",
        }}
      >
        {uploading ? <div className="spinner spinner-lg" /> : "📤"}
      </div>
      <div style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: 8 }}>
        {uploading ? "Uploading…" : "Drop a file here"}
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: 0 }}>
        {uploading
          ? "Please wait while your file is being uploaded"
          : "or click to browse — only PDF supported"}
      </p>
    </div>
  );
}
function DocCard({
  doc,
  onQuery,
  onView,
}: {
  doc: DocumentResponse;
  onQuery: (id: string) => void;
  onView: (id: string) => void;
}) {
  const [loadingView, setLoadingView] = useState(false);
  const handleView = async () => {
    setLoadingView(true);
    try {
      await onView(doc.id);
    } finally {
      setLoadingView(false);
    }
  };
  return (
    <div className="card doc-card animate-fade-up">
      <div className="doc-card-header">
        <div className="doc-icon">📄</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="doc-filename truncate">{doc.filename}</div>
          <div className="doc-meta">
            <span>{formatDate(doc.created_at)}</span>
          </div>
        </div>
        <StatusBadge status={doc.status} />
      </div>
      {doc.error && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "#f87171",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius-sm)",
            padding: "6px 10px",
          }}
        >
          ⚠️ {doc.error}
        </div>
      )}
      <div className="doc-actions">
        <button
          id={`view-doc-${doc.id}`}
          className="btn btn-secondary btn-sm"
          onClick={handleView}
          disabled={loadingView || doc.status !== "ready"}
          title="View PDF"
        >
          {loadingView ? <div className="spinner spinner-sm" /> : "👁️"}
          View
        </button>
        <button
          id={`query-doc-${doc.id}`}
          className="btn btn-primary btn-sm"
          onClick={() => onQuery(doc.id)}
          disabled={doc.status !== "ready"}
          title="Query this document"
        >
          💬 Query
        </button>
      </div>
    </div>
  );
}
export default function DocumentsPage() {
  const {
    documents,
    loading,
    error,
    uploading,
    uploadFile,
    getViewUrl,
  } = useDocuments();
  const router = useRouter();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const handleUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);
    try {
      await uploadFile(file);
      setUploadSuccess(`"${file.name}" uploaded — processing will begin shortly.`);
      setTimeout(() => setUploadSuccess(null), 5000);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    }
  };
  const handleView = async (id: string) => {
    const url = await getViewUrl(id);
    window.open(url, "_blank", "noopener noreferrer");
  };
  const handleQuery = (id: string) => {
    router.push(`/query?doc=${encodeURIComponent(id)}`);
  };
  return (
    <>
      <div className="page-header">
        <h1 style={{ marginBottom: 4 }}>Documents</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          Upload and manage your documents for AI-powered Q&amp;A
        </p>
      </div>
      <div className="page-content">
        {/* Upload zone */}
        <UploadZone onUpload={handleUpload} uploading={uploading} />
        {/* Feedback messages */}
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
          {uploadError && (
            <div className="alert alert-error animate-fade-in">
              <span>⚠️</span>
              <span>{uploadError}</span>
            </div>
          )}
          {uploadSuccess && (
            <div className="alert alert-success animate-fade-in">
              <span>✅</span>
              <span>{uploadSuccess}</span>
            </div>
          )}
          {error && (
            <div className="alert alert-error animate-fade-in">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}
        </div>
        {/* Document grid */}
        <div style={{ marginTop: 28 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 16,
            }}
          >
            <h3>
              Your Documents{" "}
              {documents.length > 0 && (
                <span
                  className="badge badge-violet"
                  style={{ fontSize: "0.75rem", verticalAlign: "middle", marginLeft: 8 }}
                >
                  {documents.length}
                </span>
              )}
            </h3>
          </div>
          {loading ? (
            <div className="doc-grid">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="skeleton"
                  style={{ height: 160, borderRadius: "var(--radius-lg)" }}
                />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📂</div>
              <h3>No documents yet</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                Upload your first document above to get started
              </p>
            </div>
          ) : (
            <div className="doc-grid stagger-children">
              {documents.map((doc) => (
                <DocCard
                  key={doc.id}
                  doc={doc}
                  onQuery={handleQuery}
                  onView={handleView}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
