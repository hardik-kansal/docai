"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { ingestionApi, ApiError } from "@/lib/api";
import type { DocumentResponse, PresignedURLResponse } from "@/lib/types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDocuments = useCallback(async () => {
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
        // Not authenticated yet — skip silently
        return;
      }
      setError("Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Poll every 3s when any document is processing/pending
  useEffect(() => {
    const hasInProgress = documents.some(
      (d) =>
        d.status === "pending" ||
        d.status === "processing" ||
        d.status === "pending_embedding"
    );

    if (hasInProgress) {
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchDocuments, 3000);
      }
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }

    return () => {
      // Don't clear on every re-render — only let the else-branch above clear it.
      // (The interval is properly cleared when component unmounts via useEffect cleanup.)
    };
  }, [documents, fetchDocuments]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

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

        // Refresh after a short delay for the webhook to fire
        setTimeout(fetchDocuments, 2000);
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
