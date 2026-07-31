"use client";

import { useState, useRef, useEffect } from "react";
import { useIngestionStatus, IngestionPhase, IngestionStatus } from "@/hooks/useIngestionStatus";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  getOrCreateThread?: () => Promise<string>;
}

/** Phase-aware progress indicator for document ingestion */
function IngestionProgress({
  phase,
  status,
  chunkCount,
  totalChunks,
  batch,
  totalBatches,
  error,
  onCancel,
}: {
  phase: IngestionPhase;
  status: IngestionStatus;
  chunkCount: number;
  totalChunks: number;
  batch?: number;
  totalBatches?: number;
  error?: string;
  onCancel: () => void;
}) {
  const phaseLabels: Record<IngestionPhase, string> = {
    connecting: "Connecting...",
    extracting: "Extracting text from PDF...",
    filtering: "Filtering relevant sections...",
    chunking: totalChunks > 0 ? `Splitting into ${totalChunks} chunks...` : "Splitting into chunks...",
    embedding:
      totalChunks > 0
        ? `Embedding chunks ${chunkCount}/${totalChunks}...`
        : "Embedding chunks...",
    complete: "Done",
  };

  const progressPct =
    phase === "embedding" && totalChunks > 0
      ? Math.round((chunkCount / totalChunks) * 100)
      : phase === "complete"
        ? 100
        : undefined;

  if (phase === "complete" && status === "cancelled") {
    return (
      <div className="flex items-center gap-2 text-xs font-medium text-loss">
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
        Upload cancelled
      </div>
    );
  }

  if (phase === "complete" && status === "error") {
    return (
      <div className="flex items-center gap-2 text-xs font-medium text-loss">
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        {error || "Ingestion failed"}
      </div>
    );
  }

  // Active ingestion — show phase + progress bar + cancel button
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium" style={{ color: "var(--accent)" }}>
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {phaseLabels[phase]}
          {batch && totalBatches && phase === "embedding" && (
            <span className="text-text-muted font-mono text-[10px]">
              batch {batch}/{totalBatches}
            </span>
          )}
        </div>
        <button
          onClick={onCancel}
          className="text-[10px] font-medium px-2 py-0.5 rounded transition-colors hover:bg-loss-muted"
          style={{ color: "var(--loss)", border: "1px solid var(--loss)", background: "transparent" }}
        >
          Cancel
        </button>
      </div>
      {progressPct !== undefined && (
        <div className="w-full h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-panel-muted)" }}>
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%`, background: "var(--accent)" }}
          />
        </div>
      )}
    </div>
  );
}

export function ChatInput({ onSend, disabled, getOrCreateThread }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [uploadingDocId, setUploadingDocId] = useState<string | null>(null);
  const [activeDoc, setActiveDoc] = useState<{title: string, chunks: number} | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadingTitle, setUploadingTitle] = useState<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // WebSocket-based ingestion tracking
  const ingestion = useIngestionStatus(uploadingDocId);

  // React to ingestion completion
  useEffect(() => {
    if (!uploadingDocId) return;

    if (ingestion.status === "ready" || ingestion.status === "partial") {
      setActiveDoc({ title: uploadingTitle, chunks: ingestion.chunkCount });
      setUploadingDocId(null);
      setUploadingTitle("");
    } else if (ingestion.status === "error" || ingestion.status === "cancelled") {
      setUploadError(
        ingestion.status === "cancelled"
          ? "Upload was cancelled"
          : ingestion.error || "Ingestion failed"
      );
      setUploadingDocId(null);
      setUploadingTitle("");
    }
  }, [ingestion.status, ingestion.chunkCount, ingestion.error, uploadingDocId, uploadingTitle]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      setUploadError("Only PDF files are supported");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError("File too large (max 50MB)");
      return;
    }

    setUploadError(null);

    try {
      const threadId = getOrCreateThread ? await getOrCreateThread() : null;
      if (!threadId) throw new Error("Could not create thread");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("thread_id", threadId);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Upload failed");
      }

      const data = await res.json();
      // Store doc ID — this triggers the useIngestionStatus hook to open a WS connection
      setUploadingTitle(data.title);
      setUploadingDocId(data.document_id);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const isIngesting = uploadingDocId !== null && ingestion.status === "processing";

  return (
    <div className="border-t bg-panel p-4 relative z-10"
         style={{ borderColor: "var(--border)" }}>
      <div className="max-w-3xl mx-auto flex flex-col gap-2">
        {/* Document Status Badge */}
        {activeDoc && (
          <div className="flex items-center gap-2 self-start text-xs font-medium px-2.5 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Document Mode: {activeDoc.title}
          </div>
        )}

        {/* Ingestion Progress */}
        {isIngesting && (
          <IngestionProgress
            phase={ingestion.phase}
            status={ingestion.status}
            chunkCount={ingestion.chunkCount}
            totalChunks={ingestion.totalChunks}
            batch={ingestion.batch}
            totalBatches={ingestion.totalBatches}
            error={ingestion.error}
            onCancel={ingestion.cancel}
          />
        )}

        {/* Upload error */}
        {uploadError && !isIngesting && (
          <div className="text-xs text-loss font-medium px-2">
            {uploadError}
          </div>
        )}

        {/* Hint text */}
        {!activeDoc && !uploadError && !isIngesting && (
          <div className="text-xs text-text-muted px-2">
            Upload a PDF to enable document Q&A for this conversation
          </div>
        )}

        <div className="flex items-end gap-3">
          {/* Hidden File Input */}
          <input
            type="file"
            accept=".pdf"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileUpload}
          />
          
          {/* Upload Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isIngesting}
            className="p-3 rounded-lg flex-shrink-0 transition-colors bg-panel border border-border hover:bg-panel-muted disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Upload document"
            title="Upload PDF for Q&A"
          >
            <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>

          <div className="flex-1 rounded-lg p-1 transition-colors bg-panel"
               style={{ border: "1px solid var(--border)" }}>
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about any US or Indian stock…"
              disabled={disabled || isIngesting}
              rows={1}
              id="chat-input"
              className="w-full bg-transparent resize-none text-base px-3 py-2.5 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                color: "var(--text-primary)",
                fontFamily: "var(--font-body)",
              }}
            />
          </div>

          <button
            onClick={handleSend}
            disabled={disabled || !value.trim() || isIngesting}
            id="send-button"
            className="p-3 rounded-lg flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            style={{
              background: "var(--accent)",
              color: "#fff",
            }}
            aria-label="Send message"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
