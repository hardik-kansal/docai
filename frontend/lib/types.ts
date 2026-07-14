// ─── Auth ───────────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  pwd: string;
}

export interface SignupResponse {
  message: string;
  user_id: string;
}

export interface LoginResponse {
  message: string;
  user_id: string;
}

export interface UserProfile {
  user_id: string;
  username: string;
  scopes: string[];
  plan_type: string;
  storage_used_bytes: number;
  created_at: string;
}

// ─── Documents ──────────────────────────────────────────────────────────────

export type DocumentStatus =
  | "pending"
  | "processing"
  | "chunking"
  | "ready"
  | "error"
  | "pending_embedding";

export interface DocumentResponse {
  id: string;
  filename: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  s3_key: string;
  error: string | null;
}

export interface PresignedURLResponse {
  upload_url: string;                      // actual MinIO POST endpoint URL
  upload_fields: Record<string, string>;   // auth fields to include in multipart form
  object_key: string;
  expires_in: number;
}

export interface ViewURLResponse {
  view_url: string;
  expires_in: number;
}

// ─── Query / LLM Output ─────────────────────────────────────────────────────

export interface ContextChunk {
  document_id: string;
  chunk_index: number;
  page_numbers: number[];
  contextualized_text: string;
}

export type AbstainReason =
  | "none"
  | "input_rejected"
  | "no_relevant_context"
  | "generation_unavailable"
  | "low_groundedness";

export interface GroundedAnswer {
  answer: string;
  confidence: number;
  abstained: boolean;
  abstain_reason: AbstainReason;
}

export interface UsageStats {
  input_tokens: number;
  output_tokens: number;
  thought_tokens: number;
  total_tokens: number;
}

// ─── SSE Stream Events ───────────────────────────────────────────────────────

export type StreamEvent =
  | { type: "started" }
  | { type: "thought"; content: string }
  | { type: "structured_json_data"; content: string }
  | { type: "usage"; content: UsageStats }
  | { type: "context"; content: ContextChunk[] }
  | { type: "error"; content: string };

// ─── Query Request ───────────────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  document_ids?: string[] | null;
}

// ─── Chat message (client-side) ──────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  // assistant-only
  groundedAnswer?: GroundedAnswer;
  contextChunks?: ContextChunk[];
  usage?: UsageStats;
  thoughts?: string;
  isStreaming?: boolean;
  isThinking?: boolean;
  error?: string;
}

// ─── Plan ────────────────────────────────────────────────────────────────────

export type PlanType = "FREE";

export const PLAN_STORAGE_BYTES: Record<PlanType, number> = {
  FREE: 2 * 1024 * 1024 * 1024, // 2 GB
};
