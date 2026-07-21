import type {
  LoginRequest,
  LoginResponse,
  SignupResponse,
  UserProfile,
  DocumentResponse,
  PresignedURLResponse,
  ViewURLResponse,
  QueryRequest,
} from "./types";

// Base fetch wrapper — all requests go through Next.js rewrites → backend
async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(path, {
    credentials: "include", // send httpOnly cookies
    cache: "no-store", // disable Next.js client-side/server-side fetch caching
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export const authApi = {
  getGoogleAuthUrl(): Promise<{ url: string }> {
    return apiFetch("/api/v1/auth/login/google");
  },

  logout(): Promise<{ message: string }> {
    return apiFetch("/api/v1/auth/logout", { method: "POST" });
  },

  me(): Promise<UserProfile> {
    return apiFetch("/api/v1/auth/me");
  },
};

// ─── Ingestion ───────────────────────────────────────────────────────────────

export const ingestionApi = {
  listDocuments(): Promise<DocumentResponse[]> {
    return apiFetch("/api/v1/ingestion/documents");
  },

  getUploadUrl(filename: string): Promise<PresignedURLResponse> {
    return apiFetch(
      `/api/v1/ingestion/get-upload-url?filename=${encodeURIComponent(filename)}`
    );
  },

  getViewUrl(documentId: string): Promise<ViewURLResponse> {
    return apiFetch(`/api/v1/ingestion/documents/${documentId}/view-url`);
  },

  deleteDocument(documentId: string): Promise<{ detail: string, document_id: string }> {
    return apiFetch(`/api/v1/ingestion/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  /**
   * Upload a file directly to MinIO via presigned POST URL.
   * Returns HTTP status of the S3 upload response.
   */
  async uploadToStorage(
    presignedUrl: string,
    file: File
  ): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(presignedUrl, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new ApiError(res.status, "File upload to storage failed");
    }
  },
};

// ─── Query (SSE streaming) ───────────────────────────────────────────────────

/**
 * Opens an SSE stream to the query endpoint.
 * Returns a raw Response — callers use lib/stream.ts to parse events.
 */
export async function postQuery(req: QueryRequest): Promise<Response> {
  const res = await fetch("/api/v1/query", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    // For abstain / guard-rail rejections, the backend returns JSON directly
    // with a non-2xx status
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    throw new ApiError(res.status, JSON.stringify(body));
  }

  return res;
}
