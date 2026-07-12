import type { StreamEvent, GroundedAnswer } from "./types";

/**
 * Parse an SSE line of the form:
 *   data: {"type":"thought","content":"..."}
 * Returns the parsed StreamEvent or null if the line is empty/non-data.
 */
function parseLine(line: string): StreamEvent | null {
  if (!line.startsWith("data: ")) return null;
  const raw = line.slice(6).trim();
  if (!raw || raw === "[DONE]") return null;
  try {
    return JSON.parse(raw) as StreamEvent;
  } catch {
    return null;
  }
}

export interface StreamCallbacks {
  onStarted?: () => void;
  onThought?: (chunk: string) => void;
  onJsonChunk?: (chunk: string) => void;
  onUsage?: (usage: import("./types").UsageStats) => void;
  onError?: (msg: string) => void;
  onComplete?: (answer: GroundedAnswer | null) => void;
}

/**
 * Reads a fetch Response body as an SSE stream and fires callbacks per event.
 * Accumulates `structured_json_data` chunks and parses GroundedAnswer at end.
 */
export async function parseStream(
  response: Response,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  if (!response.body) {
    callbacks.onError?.("Response body is empty");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulatedJson = "";

  try {
    while (true) {
      if (signal?.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by double newlines
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? ""; // last part may be incomplete

      for (const part of parts) {
        const lines = part.split("\n");
        for (const line of lines) {
          const event = parseLine(line);
          if (!event) continue;

          switch (event.type) {
            case "started":
              callbacks.onStarted?.();
              break;

            case "thought":
              callbacks.onThought?.(event.content);
              break;

            case "structured_json_data": {
              accumulatedJson += event.content;
              const match = accumulatedJson.match(/"answer"\s*:\s*"((?:[^"\\]|\\.)*)/);
              let partial = accumulatedJson;
              if (match) {
                try {
                  partial = JSON.parse(`"${match[1]}"`);
                } catch {
                  partial = match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
                }
              }
              callbacks.onJsonChunk?.(partial);
              break;
            }

            case "usage":
              callbacks.onUsage?.(event.content);
              break;

            case "error":
              callbacks.onError?.(event.content);
              break;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  // Parse accumulated JSON into GroundedAnswer
  if (accumulatedJson.trim()) {
    try {
      const answer = JSON.parse(accumulatedJson) as GroundedAnswer;
      callbacks.onComplete?.(answer);
    } catch {
      // Backend may have streamed a non-JSON abstain response
      callbacks.onComplete?.(null);
    }
  } else {
    callbacks.onComplete?.(null);
  }
}
