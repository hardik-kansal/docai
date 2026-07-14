"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { postQuery, ApiError } from "@/lib/api";
import { parseStream } from "@/lib/stream";
import type { ChatMessage, GroundedAnswer, UsageStats } from "@/lib/types";

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useQuery() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const updateMessage = useCallback(
    (id: string, patch: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, ...patch } : m))
      );
    },
    []
  );

  useEffect(() => {
    const handleQueryProgress = (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      setMessages((prev) => {
        if (prev.length === 0) return prev;
        const lastMsg = prev[prev.length - 1];
        if (lastMsg.role === "assistant" && lastMsg.isThinking) {
          return [
            ...prev.slice(0, -1),
            { ...lastMsg, thoughts: (lastMsg.thoughts ?? "") + customEvent.detail + "\n\n" }
          ];
        }
        return prev;
      });
    };

    window.addEventListener("query_progress", handleQueryProgress);
    return () => window.removeEventListener("query_progress", handleQueryProgress);
  }, []);

  const sendQuery = useCallback(
    async (queryText: string, documentIds?: string[] | null): Promise<void> => {
      if (isStreaming) return;

      // Add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: queryText,
        timestamp: new Date(),
      };

      // Add empty assistant placeholder
      const assistantId = generateId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
        isThinking: true,
        thoughts: "",
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      abortRef.current = new AbortController();

      try {
        const response = await postQuery({
          query: queryText,
          document_ids: documentIds ?? null,
        });

        await parseStream(
          response,
          {
            onStarted: () => {
              updateMessage(assistantId, { isThinking: true });
            },

            onThought: (chunk) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, thoughts: (m.thoughts ?? "") + chunk }
                    : m
                )
              );
            },

            onJsonChunk: (chunk) => {
              // Show streaming text as raw content while accumulating
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        isThinking: false,
                        content: chunk,
                      }
                    : m
                )
              );
            },

            onContext: (chunks) => {
              updateMessage(assistantId, { contextChunks: chunks });
            },

            onUsage: (usage: UsageStats) => {
              updateMessage(assistantId, { usage });
            },

            onError: (msg) => {
              updateMessage(assistantId, {
                error: msg,
                isStreaming: false,
                isThinking: false,
              });
            },

            onComplete: (answer: GroundedAnswer | null) => {
              if (answer) {
                updateMessage(assistantId, {
                  content: answer.answer,
                  groundedAnswer: answer,
                  isStreaming: false,
                  isThinking: false,
                });
              } else {
                updateMessage(assistantId, {
                  isStreaming: false,
                  isThinking: false,
                });
              }
            },
          },
          abortRef.current.signal
        );
      } catch (err) {
        let errorMsg = "Something went wrong. Please try again.";

        if (err instanceof ApiError) {
          // Backend may return a GroundedAnswer-shaped JSON in the error body
          try {
            const parsed = JSON.parse(err.message) as GroundedAnswer;
            updateMessage(assistantId, {
              content: parsed.answer,
              groundedAnswer: parsed,
              isStreaming: false,
              isThinking: false,
            });
            return;
          } catch {
            errorMsg = err.message;
          }
        }

        updateMessage(assistantId, {
          error: errorMsg,
          isStreaming: false,
          isThinking: false,
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, updateMessage]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming
          ? { ...m, isStreaming: false, isThinking: false }
          : m
      )
    );
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isStreaming, sendQuery, cancelStream, clearMessages };
}
