/**
 * SSE stream consumer using fetch + ReadableStream.
 * EventSource only supports GET — our chat endpoint is POST.
 */

export type SSEEvent = {
  event: string;
  data: unknown;
};

export type SSECallbacks = {
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
};

// For SSE streams, connect directly to the backend to avoid
// Next.js rewrite proxy buffering (which can hold chunks until stream closes).
const SSE_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function streamChat(
  threadId: string,
  content: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(
    `${SSE_BASE}/api/v1/threads/${threadId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    }
  );

  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error");
    callbacks.onError?.(new Error(`API error ${res.status}: ${errorText}`));
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError?.(new Error("No response body"));
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || "";

      let currentEvent = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ") && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            callbacks.onEvent({ event: currentEvent, data });

            if (currentEvent === "done") {
              callbacks.onDone?.();
              return;
            }
          } catch {
            // Skip malformed JSON
          }
          currentEvent = "";
        }
      }
    }
    // If we exit the loop and didn't see the 'done' event, we should still call onDone to clean up UI state
    callbacks.onDone?.();
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    callbacks.onError?.(err as Error);
  } finally {
    reader.releaseLock();
  }
}
