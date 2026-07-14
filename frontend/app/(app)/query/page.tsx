"use client";
import {
  useRef,
  useEffect,
  useState,
  KeyboardEvent,
  Suspense,
  useCallback,
} from "react";
import ReactMarkdown from 'react-markdown';
import { useSearchParams } from "next/navigation";
import { useQuery } from "@/hooks/useQuery";
import { useDocuments } from "@/hooks/useDocuments";
import type {
  ChatMessage,
  ContextChunk,
  UsageStats,
  DocumentResponse,
  DocumentStatus,
} from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function StatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { cls: string; label: string }> = {
    pending:           { cls: "badge-pending",    label: "⏳ Pending"    },
    processing:        { cls: "badge-processing", label: "⚙️ Processing" },
    chunking:          { cls: "badge-processing", label: "✂️ Chunking"   },
    pending_embedding: { cls: "badge-processing", label: "🔄 Embedding"  },
    ready:             { cls: "badge-ready",      label: "Active"      },
    error:             { cls: "badge-error",      label: "❌ Error"      },
  };
  const safeStatus = (status || "").toLowerCase() as DocumentStatus;
  const conf = map[safeStatus] ?? map.pending;
  return <span className={`badge ${conf.cls}`}>{conf.label}</span>;
}

// ─── Left document panel ──────────────────────────────────────────────────────

function DocumentPanel({
  documents,
  uploading,
  selectedDocs,
  onToggleDoc,
  onSelectAll,
  onDeselectAll,
  onDrop,
  onDragOver,
  onDragLeave,
  dragging,
  uploadMsg,
  onFileSelect,
}: {
  documents: DocumentResponse[];
  uploading: boolean;
  selectedDocs: Set<string>;
  onToggleDoc: (id: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  dragging: boolean;
  uploadMsg: { type: "success" | "error"; text: string } | null;
  onFileSelect: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div
      className="ubuntu-sidebar"
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      style={{
        width: 350, /* SIDEBAR WIDTH: You can change this number (e.g. 360) to make it wider */
        flexShrink: 0,
        borderRight: "1px solid var(--border-subtle)",
        background: dragging ? "var(--rose-50)" : "var(--bg-surface)",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
        transition: "background var(--transition-base)"
      }}
    >
      {/* Folder Tab Header */}
      <div 
        className="ubuntu-folder-tab" 
        style={{ 
          marginTop: 20, 
          marginLeft: 0, 
          height: 34, 
          padding: "0 28px 0 20px", 
          alignSelf: "flex-start",
        }}
      >
        <span style={{ fontSize: "1rem", marginRight: 8 }}>📁</span>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#fff", letterSpacing: "0.02em" }}>
          My Documents
        </span>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        
        {/* Upload drop zone (Top half) */}
        <div
          className="ubuntu-folder-drop-zone"
          onClick={() => !uploading && fileRef.current?.click()}
          style={{
            flex: "0 0 35%", /* DROP AREA HEIGHT */
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            cursor: uploading ? "not-allowed" : "pointer",
            borderTopLeftRadius: 0,
            marginLeft: 0,
            marginRight: 0,
            marginTop: -3, /* overlap the tab slightly */
            position: "relative",
            zIndex: 1,
            background: dragging ? "var(--rose-50)" : "rgba(255,255,255,0.4)",
            boxShadow: dragging ? "inset 0 0 0 2px var(--rose-400)" : "none"
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
            id="file-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onFileSelect(file);
              e.target.value = "";
            }}
            disabled={uploading}
          />
          {uploading ? (
            <div className="spinner spinner-md" style={{ marginBottom: 12, borderColor: "rgba(0,0,0,0.1)", borderTopColor: "#dd4814" }} />
          ) : (
            <div className="ubuntu-folder-dash" style={{ background: "var(--border-default)" }} />
          )}
          <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 600 }}>
            {uploading ? "Uploading…" : (dragging ? "Drop here! (PDF only)" : "Drop or click to upload (PDF only)")}
          </div>
        </div>

      {/* Upload feedback */}
      {uploadMsg && (
        <div
          className={`alert ${uploadMsg.type === "success" ? "alert-success" : "alert-error"} animate-fade-in`}
          style={{ margin: "8px 10px 0", fontSize: "0.75rem", padding: "8px 10px" }}
        >
          <span>{uploadMsg.type === "success" ? "✅" : "⚠️"}</span>
          <span>{uploadMsg.text}</span>
        </div>
      )}

      {documents.length > 0 && (
        <div style={{ padding: "10px 14px 4px", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Click active docs
          </div>
          {!uploading && (
            <button 
              onClick={() => selectedDocs.size > 0 ? onDeselectAll() : onSelectAll()}
              style={{
                fontSize: "0.68rem", 
                background: "transparent", 
                border: "none", 
                borderRadius: "4px", 
                color: "var(--text-secondary)", 
                padding: "2px 6px",
                cursor: "pointer",
                fontWeight: 600
              }}
            >
              {selectedDocs.size > 0 ? "Clear All" : "Select All"}
            </button>
          )}
        </div>
      )}

      {/* Document list — ALL docs including pending */}
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 8px 12px" }}>
        {documents.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "0.78rem", padding: "28px 8px" }}>
            No documents yet.<br />Upload one above.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {documents.map((doc, index) => {
              const isReady = doc.status === "ready";
              const isSelected = selectedDocs.has(doc.id);
              return (
                <div
                  key={`${doc.id}-${index}`}
                  id={`doc-item-${doc.id}-${index}`}
                  className={`doc-list-item ${isReady ? "ready-doc" : ""}`}
                  onClick={() => isReady && onToggleDoc(doc.id)}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    padding: "8px 10px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border-subtle)",
                    cursor: isReady ? "pointer" : "default",
                    transition: "all var(--transition-fast)",
                    opacity: isReady ? 1 : 0.7,
                  }}
                >
                  {/* Selection circle */}
                  {isReady && (
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        marginTop: 1,
                        borderRadius: "50%",
                        border: isSelected ? "none" : "1px solid var(--border-default)",
                        background: "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        transition: "all var(--transition-fast)",
                      }}
                    >
                      {isSelected && <span style={{ color: "var(--status-ready)", fontSize: "0.85rem", fontWeight: 700 }}>✓</span>}
                    </div>
                  )}

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      className="truncate"
                      style={{ fontSize: "0.78rem", fontWeight: 600, marginBottom: 3, lineHeight: 1.3 }}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4 }}>
                      <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>{formatDate(doc.created_at)}</span>
                      <StatusBadge status={doc.status} />
                    </div>
                    {doc.error && (
                      <div style={{ fontSize: "0.65rem", color: "#dc2626", marginTop: 3 }} title={doc.error}>
                        ⚠️ {doc.error.slice(0, 40)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
    </div>
  );
}

// ─── Chat answer components ───────────────────────────────────────────────────

function ThoughtDropdown({ text, isThinking }: { text: string; isThinking: boolean }) {
  const [isOpen, setIsOpen] = useState(isThinking);

  useEffect(() => {
    if (isThinking) setIsOpen(true);
  }, [isThinking]);

  if (!text && !isThinking) return null;

  return (
    <div className="thinking-panel" style={{ marginBottom: "12px" }}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" }}
      >
        {isThinking ? (
          <div className="thinking-dots"><span /><span /><span /></div>
        ) : (
          <span style={{ fontSize: "0.7rem", transition: "transform 0.2s", transform: isOpen ? "rotate(90deg)" : "rotate(0deg)", color: "var(--text-muted)" }}>▶</span>
        )}
        <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-muted)" }}>
          {isThinking ? "Thinking..." : "View thought process"}
        </span>
      </div>
      {isOpen && text && (
        <div style={{ marginTop: "8px", marginLeft: "4px", paddingLeft: "14px", borderLeft: "3px solid var(--border-subtle)", fontSize: "0.9rem", fontStyle: "italic", whiteSpace: "pre-wrap", color: "var(--text-muted)", maxHeight: "600px", overflowY: "auto", lineHeight: "1.6" }}>
          {text}
        </div>
      )}
    </div>
  );
}

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const cls = pct >= 70 ? "confidence-high" : pct >= 40 ? "confidence-mid" : "confidence-low";
  const label = pct >= 70 ? "High" : pct >= 40 ? "Moderate" : "Low";
  return (
    <div className={`confidence-meter ${cls}`}>
      <div className="confidence-label">
        <span>Confidence</span>
        <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>{label} ({pct}%)</span>
      </div>
      <div className="progress-bar-track"><div className="progress-bar-fill" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function ContextList({ chunks, documents }: { chunks: ContextChunk[], documents: DocumentResponse[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(false);
  if (chunks.length === 0) return null;

  const displayLimit = 2;
  const visibleChunks = showAll ? chunks : chunks.slice(0, displayLimit);
  const hiddenCount = chunks.length - displayLimit;

  return (
    <div className="citations-section">
      <div className="citations-header">📎 Sources ({chunks.length})</div>
      {visibleChunks.map((c, idx) => {
        const docName = documents.find((d) => d.id === c.document_id)?.filename ?? "Unknown Document";
        const open = expanded.has(idx);
        return (
          <div key={`${c.document_id}-${idx}`} className="citation-card" onClick={() => setExpanded((prev) => { const next = new Set(prev); open ? next.delete(idx) : next.add(idx); return next; })}>
            <div className="citation-id">Citation {idx}</div>
            <div style={{ maxHeight: open ? "400px" : "0px", overflow: "hidden", transition: "max-height 0.3s ease", lineHeight: 1.6, opacity: open ? 1 : 0 }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "8px", background: "var(--bg-base)", padding: "4px 8px", borderRadius: "4px" }}>
                <div><strong>Document:</strong> {docName}</div>
                <div><strong>Chunk Index:</strong> {c.chunk_index}</div>
                <div><strong>Page No:</strong> {c.page_numbers?.join(", ") ?? "N/A"}</div>
              </div>
              <div style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{c.contextualized_text}</div>
            </div>
            {!open && <div style={{ fontSize: "0.85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.contextualized_text.substring(0, 100)}...</div>}
            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 3 }}>{open ? "▲ Collapse" : "▼ Expand"}</div>
          </div>
        );
      })}
      {hiddenCount > 0 && (
        <button 
          onClick={() => setShowAll(!showAll)}
          style={{
            background: "transparent",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-muted)",
            fontSize: "0.75rem",
            fontWeight: 600,
            cursor: "pointer",
            padding: "6px 12px",
            marginTop: "6px",
            width: "100%",
            textAlign: "center",
            transition: "all 0.2s"
          }}
        >
          {showAll ? "Show fewer chunks ▲" : `Show ${hiddenCount} more chunks ▼`}
        </button>
      )}
    </div>
  );
}

function UsageBar({ usage }: { usage: UsageStats }) {
  return (
    <div className="usage-bar-container">
      <div className="usage-header">Token Usage</div>
      <div className="usage-bar">
        <div className="usage-item"><span>📥</span><strong>{usage.input_tokens.toLocaleString()}</strong> input</div>
        <div className="usage-item"><span>📤</span><strong>{usage.output_tokens.toLocaleString()}</strong> output</div>
        <div className="usage-item"><span>🧠</span><strong>{usage.thought_tokens.toLocaleString()}</strong> thoughts</div>
        <div className="usage-item"><span>⚡</span><strong>{usage.total_tokens.toLocaleString()}</strong> total</div>
      </div>
    </div>
  );
}

function AssistantMessage({ msg, documents }: { msg: ChatMessage, documents: DocumentResponse[] }) {
  return (
    <div className="message-bubble assistant">
      <div className="message-avatar">🤖</div>
      <div className="message-content" style={{ maxWidth: "95%", flexDirection: "row", gap: "20px" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "7px", minWidth: 0 }}>
          {(msg.isThinking || msg.thoughts) && <ThoughtDropdown text={msg.thoughts ?? ""} isThinking={msg.isThinking ?? false} />}
          {(msg.content || msg.groundedAnswer) && (
            <div className={`message-text${msg.isStreaming && !msg.groundedAnswer ? " streaming-cursor" : ""}`}>
              <ReactMarkdown>
                {msg.groundedAnswer?.answer ?? msg.content ?? ""}
              </ReactMarkdown>
            </div>
          )}
          {msg.groundedAnswer?.abstained && msg.groundedAnswer.abstain_reason && (
            <div className="abstain-notice"><div style={{ flex: 1 }}>⚠️ {msg.groundedAnswer.abstain_reason}</div></div>
          )}
          {msg.groundedAnswer && !msg.groundedAnswer.abstained && (!msg.contextChunks || msg.contextChunks.length === 0) && (
            <ConfidenceMeter confidence={msg.groundedAnswer.confidence} />
          )}
          {msg.usage && <UsageBar usage={msg.usage} />}
          {msg.error && <div className="alert alert-error" style={{ fontSize: "0.8rem" }}><span>⚠️</span><span>{msg.error}</span></div>}
          <div className="message-time">{msg.timestamp.toLocaleTimeString()}</div>
        </div>
        {msg.contextChunks && msg.contextChunks.length > 0 && (
          <div style={{ width: "320px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
            {msg.groundedAnswer && <ConfidenceMeter confidence={msg.groundedAnswer.confidence} />}
            <ContextList chunks={msg.contextChunks} documents={documents} />
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="message-bubble user">
      <div className="message-avatar">👤</div>
      <div className="message-content">
        <div className="message-text">{msg.content}</div>
        <div className="message-time">{msg.timestamp.toLocaleTimeString()}</div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

function QueryPageInner() {
  const searchParams = useSearchParams();
  const initialDoc = searchParams.get("doc");

  const { messages, isStreaming, sendQuery, cancelStream, clearMessages } = useQuery();
  const { documents, uploading, uploadFile } = useDocuments();

  const [input, setInput] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(
    initialDoc ? new Set([initialDoc]) : new Set()
  );
  const [dragging, setDragging] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle initial auto-selection and newly ready documents
  const hasInitializedSelection = useRef(false);
  const prevDocsRef = useRef(documents);

  useEffect(() => {
    // 1. Initial selection for older users
    if (!hasInitializedSelection.current && documents.length > 0) {
      const readyDocs = documents.filter(d => (d.status || "").toLowerCase() === "ready");
      if (readyDocs.length > 0 && selectedDocs.size === 0) {
        setSelectedDocs(new Set([readyDocs[0].id]));
      }
      hasInitializedSelection.current = true;
    }

    // 2. Auto-select newly ready docs
    const prev = prevDocsRef.current;
    const newlyReady = documents.filter(d => 
      (d.status || "").toLowerCase() === "ready" && 
      (prev.find(p => p.id === d.id)?.status || "").toLowerCase() !== "ready"
    );
    if (newlyReady.length > 0) {
      setSelectedDocs(s => {
        const next = new Set(s);
        newlyReady.forEach(d => next.add(d.id));
        return next;
      });
    }
    prevDocsRef.current = documents;
  }, [documents, selectedDocs.size]);

  const toggleDoc = useCallback((id: string) => {
    setSelectedDocs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAllDocs = useCallback(() => {
    setSelectedDocs(new Set(documents.filter(d => (d.status || "").toLowerCase() === "ready").map(d => d.id)));
  }, [documents]);

  const deselectAllDocs = useCallback(() => {
    setSelectedDocs(new Set());
  }, []);

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  }, []);

  const handleSend = useCallback(async () => {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await sendQuery(q, selectedDocs.size > 0 ? Array.from(selectedDocs) : null);
  }, [input, isStreaming, selectedDocs, sendQuery]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);


  const handleFileSelect = useCallback(async (file: File) => {
    setUploadMsg(null);
    if (documents.some((d) => d.filename === file.name)) {
      setUploadMsg({ type: "error", text: "Filename already exists." });
      return;
    }
    try {
      await uploadFile(file);
      setUploadMsg({ type: "success", text: `"${file.name}" uploaded — processing…` });
      setTimeout(() => setUploadMsg(null), 6000);
      // The placeholder is optimistically added in useDocuments.ts, and SSE handles real updates.
    } catch {
      setUploadMsg({ type: "error", text: "Upload failed. Please try again." });
    }
  }, [uploadFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const hasMessages = messages.length > 0;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-base)" }}>

      {/* ── Left panel: document list + upload ── */}
      <DocumentPanel
        documents={documents}
        uploading={uploading}
        selectedDocs={selectedDocs}
        onToggleDoc={toggleDoc}
        onSelectAll={selectAllDocs}
        onDeselectAll={deselectAllDocs}
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        dragging={dragging}
        uploadMsg={uploadMsg}
        onFileSelect={handleFileSelect}
      />

      {/* ── Right panel: chat + query bar ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", minWidth: 0, overflow: "hidden" }}>

        {/* Top bar */}
        <div
          style={{
            padding: "12px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
            background: "var(--bg-surface)",
          }}
        >
          <div>
            <div style={{ fontSize: "0.9rem", fontWeight: 700 }}>AI Query</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {selectedDocs.size === 0
                ? "Searching all documents"
                : `Scoped to ${selectedDocs.size} doc${selectedDocs.size > 1 ? "s" : ""}`}
            </div>
          </div>
          <div style={{ display: "flex", gap: 7 }}>
            {isStreaming && (
              <button id="cancel-stream" className="btn btn-danger btn-sm" onClick={cancelStream}>
                ⏹ Stop
              </button>
            )}
            {hasMessages && !isStreaming && (
              <button id="clear-chat" className="btn btn-ghost btn-sm" onClick={clearMessages}>
                🗑 Clear
              </button>
            )}
          </div>
        </div>

        {/* Messages area */}
        <div className="chat-messages" style={{ flex: 1 }}>
          {!hasMessages ? (
            <div className="empty-state" style={{ height: "100%" }}>
              <div className="empty-icon" style={{ fontSize: "2rem" }}>💬</div>
              <h3 style={{ fontSize: "1.1rem" }}>Ask about your documents</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: 360 }}>
                Select documents from the left panel to scope your query,
                or leave unselected to search everything.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 4 }}>
                {["Summarize the key points", "What are the main findings?", "List the important dates", "Explain the methodology"].map((s) => (
                  <button key={s} className="btn btn-secondary btn-sm" style={{ fontSize: "0.78rem" }}
                    onClick={() => { setInput(s); textareaRef.current?.focus(); }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) =>
                msg.role === "user" ? (
                  <UserMessage key={msg.id} msg={msg} />
                ) : (
                  <AssistantMessage key={msg.id} msg={msg} documents={documents} />
                )
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Query bar — bottom of the right panel */}
        <div
          style={{
            padding: "14px 20px 16px",
            borderTop: "1.5px solid var(--folder-border)",
            background: "var(--bg-surface)",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, maxWidth: 860, margin: "0 auto" }}>
            <textarea
              id="query-input"
              ref={textareaRef}
              className="folder-textarea"
              placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isStreaming}
              style={{ flex: 1 }}
            />
            <button
              id="query-send"
              className="folder-send-btn"
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              title="Send"
            >
              {isStreaming ? (
                <div className="spinner spinner-sm" style={{ borderColor: "rgba(255,255,255,0.25)", borderTopColor: "white" }} />
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>
          <div style={{ textAlign: "right", marginTop: 5, maxWidth: 860, margin: "5px auto 0" }}>
            <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{input.length}/2048 · Enter to send</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function QueryPage() {
  return (
    <Suspense fallback={<div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--bg-base)" }}><div className="spinner spinner-lg" /></div>}>
      <QueryPageInner />
    </Suspense>
  );
}
