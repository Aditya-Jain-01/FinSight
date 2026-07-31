"use client";

/**
 * WebSocket hook for real-time document ingestion progress.
 *
 * No reconnect/retry logic — since disconnect = cancel on the server,
 * reconnecting would find the ingestion dead. On any unexpected close,
 * show cancelled state and let the user re-upload.
 */

import { useState, useEffect, useRef, useCallback } from "react";

export type IngestionPhase = "connecting" | "extracting" | "filtering" | "chunking" | "embedding" | "complete";
export type IngestionStatus = "processing" | "ready" | "error" | "partial" | "cancelled";

export interface IngestionState {
  phase: IngestionPhase;
  status: IngestionStatus;
  chunkCount: number;
  totalChunks: number;
  batch?: number;
  totalBatches?: number;
  error?: string;
  cancel: () => void;
}

export function useIngestionStatus(documentId: string | null): IngestionState {
  const [phase, setPhase] = useState<IngestionPhase>("connecting");
  const [status, setStatus] = useState<IngestionStatus>("processing");
  const [chunkCount, setChunkCount] = useState(0);
  const [totalChunks, setTotalChunks] = useState(0);
  const [batch, setBatch] = useState<number | undefined>();
  const [totalBatches, setTotalBatches] = useState<number | undefined>();
  const [error, setError] = useState<string | undefined>();
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  const cancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "cancel" }));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (!documentId) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = `${apiUrl.replace(/^http/, "ws")}/api/v1/ws/documents/${documentId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      const data = JSON.parse(event.data);

      setPhase(data.phase);
      if (data.chunk_count !== undefined) setChunkCount(data.chunk_count);
      if (data.total_chunks !== undefined) setTotalChunks(data.total_chunks);
      if (data.batch !== undefined) setBatch(data.batch);
      if (data.total_batches !== undefined) setTotalBatches(data.total_batches);
      if (data.error) setError(data.error);

      if (data.phase === "complete") {
        setStatus(data.status);
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      // Disconnect = cancel on the server. If we haven't reached a terminal state,
      // the ingestion is now dead (server cancelled it). Show cancelled state.
      // Do NOT retry — reconnecting would find status="cancelled" and there's
      // nothing to resume. The user needs to re-upload.
      setStatus((prev) => {
        if (prev === "processing") {
          setPhase("complete");
          return "cancelled";
        }
        return prev;
      });
    };

    ws.onerror = () => {
      // onclose will fire after this
    };

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [documentId]);

  return { phase, status, chunkCount, totalChunks, batch, totalBatches, error, cancel };
}
