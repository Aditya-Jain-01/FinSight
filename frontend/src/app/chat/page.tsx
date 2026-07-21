"use client";

import { useEffect, useCallback, useState } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { checkHealth } from "@/lib/api";
import Link from "next/link";

export default function ChatPage() {
  const { messages, stage, error, sendMessage, retry, isStreaming } = useChat();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "waking" | "offline">("checking");

  // Check backend health on mount
  useEffect(() => {
    let cancelled = false;

    async function check() {
      setBackendStatus("checking");
      const start = Date.now();
      const healthy = await checkHealth();
      const elapsed = Date.now() - start;

      if (cancelled) return;

      if (healthy) {
        setBackendStatus("online");
      } else if (elapsed > 3000) {
        // Took too long — likely Render cold start.
        // Render free tier can take 50+ seconds to spin up, so we need to poll patiently.
        setBackendStatus("waking");
        
        let attempts = 0;
        const maxAttempts = 12; // 12 attempts * 5s = 60s of total patience

        const poll = async () => {
          if (cancelled) return;
          if (attempts >= maxAttempts) {
            setBackendStatus("offline");
            return;
          }
          
          attempts++;
          const retryHealthy = await checkHealth();
          if (cancelled) return;
          
          if (retryHealthy) {
            setBackendStatus("online");
          } else {
            setTimeout(poll, 5000);
          }
        };
        
        setTimeout(poll, 5000);
      } else {
        setBackendStatus("offline");
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  // Handle suggestion clicks from the empty state
  useEffect(() => {
    const handler = (e: Event) => {
      const content = (e as CustomEvent).detail;
      if (content && typeof content === "string") {
        sendMessage(content);
      }
    };
    window.addEventListener("suggestion-click", handler);
    return () => window.removeEventListener("suggestion-click", handler);
  }, [sendMessage]);

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content);
    },
    [sendMessage]
  );

  return (
    <div className="h-screen flex flex-col bg-page">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-panel shadow-sm relative z-10">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="text-xl font-bold font-display text-accent">
            FinSight
          </span>
        </Link>

        {/* Backend status indicator */}
        <div className="flex items-center gap-2 font-mono text-xs">
          {backendStatus === "waking" && (
            <div className="flex items-center gap-2 text-text-secondary">
              <svg className="w-3.5 h-3.5 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Waking up the server (~30s)…
            </div>
          )}
          {backendStatus === "offline" && (
            <div className="flex items-center gap-2 text-loss">
              <span className="w-1.5 h-1.5 rounded-full bg-loss" />
              Backend offline
            </div>
          )}
          {backendStatus === "online" && (
            <div className="flex items-center gap-2 text-gain">
              <span className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse" />
              Online
            </div>
          )}
        </div>
      </header>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Error banner */}
      {error && (
        <div className="px-4 py-3 bg-loss-muted border-t border-loss/20 flex items-center justify-between relative z-10">
          <span className="text-sm font-medium text-loss">{error}</span>
          <button
            onClick={retry}
            className="text-xs px-3 py-1 rounded bg-loss/10 text-loss hover:bg-loss/20 transition-colors font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Idle-State Suggestion Chips */}
      {messages.length > 0 && !isStreaming && (
        <div className="flex justify-center gap-3 mb-4 mt-2 px-4 relative z-10 animate-fade-in max-w-3xl mx-auto w-full">
          {["[ TCS's P/E ]", "[ Reliance capex plans ]", "[ Compare AAPL and MSFT ]"].map((chip) => (
            <button
              key={chip}
              className="font-mono text-[11px] px-2.5 py-1 rounded bg-panel border border-border
                         text-text-secondary hover:text-text-primary hover:bg-panel-muted transition-colors shadow-sm"
              onClick={() => handleSend(chip.replace(/[\[\]]/g, "").trim())}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={isStreaming || backendStatus === "offline"}
      />
    </div>
  );
}
