"use client";

import { useEffect, useCallback } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";

export default function ChatPage() {
  const { messages, stage, error, sendMessage, retry, isStreaming, getOrCreateThread, addLocalMessage } = useChat();

  // Handle suggestion clicks from the empty state
  useEffect(() => {
    const handler = (e: Event) => {
      const content = (e as CustomEvent).detail;
      if (content && typeof content === "string") {
        sendMessage(content);
      }
    };
    
    const marketBriefHandler = () => {
      addLocalMessage({
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "Here is the latest global market brief:",
        uiBlocks: [{ component: "MarketBrief", props: {} }],
        toolTrace: [],
      });
    };

    window.addEventListener("suggestion-click", handler);
    window.addEventListener("market-brief-click", marketBriefHandler);
    
    return () => {
      window.removeEventListener("suggestion-click", handler);
      window.removeEventListener("market-brief-click", marketBriefHandler);
    };
  }, [sendMessage, addLocalMessage]);

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content);
    },
    [sendMessage]
  );

  return (
    <div className="h-full flex flex-col">
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
        disabled={isStreaming}
        getOrCreateThread={getOrCreateThread}
      />
    </div>
  );
}
