"use client";

import { useState, useCallback, useRef } from "react";
import { createThread } from "@/lib/api";
import { streamChat, SSEEvent } from "@/lib/sse";

export interface ToolCallEntry {
  tool: string;
  args: Record<string, unknown>;
  latency_ms: number;
  raw_result: unknown;
  error: string | null;
}

export type ChatStage = "idle" | "planning" | "executing" | "responding" | "error";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  uiBlocks: unknown[];
  toolTrace: ToolCallEntry[];
  isStreaming?: boolean;
  stage?: ChatStage;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // Global stage just for disabling input
  const [stage, setStage] = useState<ChatStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const threadIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    setError(null);

    // Create thread on first message
    if (!threadIdRef.current) {
      try {
        const { thread_id } = await createThread();
        threadIdRef.current = thread_id;
      } catch (err) {
        setError("Failed to connect to the server. Is the backend running?");
        setStage("error");
        return;
      }
    }

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      uiBlocks: [],
      toolTrace: [],
    };

    // Prepare assistant message placeholder
    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      uiBlocks: [],
      toolTrace: [],
      isStreaming: true,
      stage: "planning", // Initial stage
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStage("planning");

    // Abort previous stream if any
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch { /* already aborted */ }
    }
    const controller = new AbortController();
    abortRef.current = controller;

    const accumulatedTrace: ToolCallEntry[] = [];
    const accumulatedBlocks: unknown[] = [];

    try {
    await streamChat(
      threadIdRef.current,
      content,
      {
        onEvent: (event: SSEEvent) => {
          switch (event.event) {
            case "status": {
              const data = event.data as { stage: string };
              const currentStage = data.stage as ChatStage;
              setStage(currentStage);
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, stage: currentStage };
                }
                return updated;
              });
              break;
            }
            case "tool_call": {
              setStage("executing");
              const trace = event.data as ToolCallEntry;
              accumulatedTrace.push(trace);
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    stage: "executing",
                    toolTrace: [...accumulatedTrace],
                  };
                }
                return updated;
              });
              break;
            }
            case "token": {
              setStage("responding");
              const data = event.data as { text: string };
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    stage: "responding",
                    content: data.text,
                  };
                }
                return updated;
              });
              break;
            }
            case "ui_block": {
              accumulatedBlocks.push(event.data);
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    uiBlocks: [...accumulatedBlocks],
                  };
                }
                return updated;
              });
              break;
            }
            case "error": {
              const data = event.data as { message: string };
              setError(data.message);
              setStage("error");
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant" && last.isStreaming) {
                  updated[updated.length - 1] = {
                    ...last,
                    stage: "error",
                    content: last.content || "An error occurred.",
                    isStreaming: false,
                  };
                }
                return updated;
              });
              break;
            }
          }
        },
        onError: (err: Error) => {
          setError(err.message);
          setStage("error");
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant" && last.isStreaming) {
              updated[updated.length - 1] = {
                ...last,
                stage: "error",
                content: last.content || "Something went wrong. Please try again.",
                isStreaming: false,
              };
            }
            return updated;
          });
        },
        onDone: () => {
          setStage("idle");
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              // Build AgentTrace ui_block from accumulated trace
              const traceBlock = accumulatedTrace.length > 0
                ? {
                    component: "AgentTrace",
                    props: {
                      toolCalls: accumulatedTrace,
                      totalLatencyMs: accumulatedTrace.reduce(
                        (sum, t) => sum + t.latency_ms,
                        0
                      ),
                    },
                  }
                : null;

              updated[updated.length - 1] = {
                ...last,
                isStreaming: false,
                stage: "idle",
                uiBlocks: [
                  ...accumulatedBlocks,
                  ...(traceBlock ? [traceBlock] : []),
                ],
              };
            }
            return updated;
          });
        },
      },
      controller.signal
    );
    } catch (err) {
      // Swallow AbortError from cancelled streams
      if (err instanceof DOMException && err.name === "AbortError") return;
      throw err;
    }
  }, []);

  const retry = useCallback(() => {
    setError(null);
    setStage("idle");
  }, []);

  return {
    messages,
    stage,
    error,
    sendMessage,
    retry,
    isStreaming: stage !== "idle" && stage !== "error",
  };
}
