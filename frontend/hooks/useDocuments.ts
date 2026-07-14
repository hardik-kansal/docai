"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { ingestionApi, ApiError } from "@/lib/api";
import type { DocumentResponse, PresignedURLResponse } from "@/lib/types";
import { useAuth } from "./useAuth";

export function useDocuments() {
  const { user, updateUser } = useAuth();
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const userId = user?.user_id;

  const fetchDocuments = useCallback(async () => {
    if (!userId) return; // Don't fetch if not logged in
    try {
      const docs = await ingestionApi.listDocuments();
      setDocuments((currentDocs) => {
        const realDocsFilenames = new Set(docs.map((d) => d.filename));
        const activePlaceholders = currentDocs.filter(
          (d) => d.id.startsWith("pending-") && !realDocsFilenames.has(d.filename)
        );
        return [...activePlaceholders, ...docs];
      });
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 400 || err.status === 401)) {
        return;
      }
      setError("Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // Initial fetch when user becomes available
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Listen for real-time document status updates via SSE
  useEffect(() => {
    if (!userId) return; // Wait until authenticated

    const eventSource = new EventSource("/api/v1/ingestion/check-doc-status", {
      withCredentials: true, // ensures cookies are sent for authentication
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "storage_update") {
          updateUser({ storage_used_bytes: data.storage_used_bytes });
          return;
        }

        if (data.type === "query_progress") {
          window.dispatchEvent(new CustomEvent("query_progress", { detail: data.message }));
          return;
        }

        if (data.object_key && data.status) {
          setDocuments((currentDocs) =>
            currentDocs.map((doc) =>
              doc.s3_key === data.object_key || (data.document_id && doc.id === data.document_id)
                ? { 
                    ...doc, 
                    status: data.status as DocumentResponse["status"],
                    ...(data.document_id ? { id: data.document_id } : {})
                  }
                : doc
            )
          );
        }
      } catch (err) {
        console.error("Failed to parse SSE message", err);
      }
    };

    eventSource.onerror = (err) => {
      console.log("SSE connection error", err);
      // EventSource automatically tries to reconnect, so we don't need manual reconnection logic here.
    };

    return () => {
      eventSource.close();
    };
  }, [userId]);

  /**
   * Full upload flow:
   * 1. GET presigned URL from backend
   * 2. POST file directly to MinIO
   * MinIO webhook → Celery → document appears with "pending" status
   */
  const uploadFile = useCallback(
    async (file: File): Promise<void> => {
      setUploading(true);
      setError(null);
      try {
        const presigned: PresignedURLResponse = await ingestionApi.getUploadUrl(
          file.name
        );

        // Build multipart form exactly as MinIO requires:
        // all signed fields first (in order), then the file LAST.
        // ← this is what upload_s3.py shows and what S3 spec mandates.
        const formData = new FormData();
        for (const [key, value] of Object.entries(presigned.upload_fields)) {
          formData.append(key, value);
        }
        formData.append("file", file);

        const uploadRes = await fetch(presigned.upload_url, {
          method: "POST",
          body: formData,
          // Do NOT set Content-Type header — browser sets it with the correct
          // multipart boundary automatically when body is FormData.
        });

        if (!uploadRes.ok) {
          throw new Error(`Storage upload failed: ${uploadRes.status}`);
        }

        // Optimistically add a pending placeholder while webhook fires
        const placeholder: DocumentResponse = {
          id: `pending-${Date.now()}`,
          filename: file.name,
          status: "pending",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          s3_key: presigned.object_key,
          error: null,
        };
        setDocuments((prev) => [placeholder, ...prev]);
      } catch (err) {
        const msg =
          err instanceof ApiError ? err.message : "Upload failed";
        setError(msg);
        throw err;
      } finally {
        setUploading(false);
      }
    },
    [fetchDocuments]
  );

  const getViewUrl = useCallback(
    async (documentId: string): Promise<string> => {
      const res = await ingestionApi.getViewUrl(documentId);
      return res.view_url;
    },
    []
  );

  return {
    documents,
    loading,
    error,
    uploading,
    fetchDocuments,
    uploadFile,
    getViewUrl,
  };
}
