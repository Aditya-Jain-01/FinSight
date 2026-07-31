"use client";

import { useRef, useEffect } from "react";
import { ChatMessage } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <h2 className="text-xl font-display font-semibold text-text-primary mb-3">
          What would you like to research?
        </h2>
        <p className="text-sm text-text-secondary max-w-md mb-8">
          Ask about any US or Indian stock — prices, financials, company profiles, or recent news.
        </p>
        <div className="flex flex-col gap-3 justify-center max-w-sm w-full">
          {[
            "What is Apple's current stock price?",
            "What is Reliance's current stock price?",
            "Show me TCS financials and P/E ratio",
            "What's the latest news on HDFC Bank?",
          ].map((suggestion) => (
            <button
              key={suggestion}
              className="font-mono text-xs px-4 py-3 rounded bg-panel border border-border
                         text-text-primary hover:bg-panel-muted transition-colors text-center shadow-sm"
              onClick={() => {
                const event = new CustomEvent("suggestion-click", {
                  detail: suggestion,
                });
                window.dispatchEvent(event);
              }}
            >
              [ {suggestion} ]
            </button>
          ))}
          <button
            className="font-mono text-xs px-4 py-3 rounded bg-accent/10 border border-accent/20
                       text-accent font-semibold hover:bg-accent/20 transition-colors text-center shadow-sm mt-2"
            onClick={() => {
              const event = new CustomEvent("market-brief-click");
              window.dispatchEvent(event);
            }}
          >
            [ View Market Brief ]
          </button>
        </div>
      </div>
    );
  }

  // Find the last assistant message that contains a StockOverview block.
  // Only that message's StockOverview gets a live WebSocket connection.
  const lastStockOverviewMsgId = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role === "assistant" && msg.uiBlocks.some(
        (b: any) => b && typeof b === "object" && "component" in b && b.component === "StockOverview"
      )) {
        return msg.id;
      }
    }
    return null;
  })();

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8" id="message-list">
      <div className="max-w-3xl mx-auto space-y-8">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isLatestStockOverview={msg.id === lastStockOverviewMsgId}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
