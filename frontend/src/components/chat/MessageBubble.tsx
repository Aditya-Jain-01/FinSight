"use client";

import { useState } from "react";
import { ChatMessage, ChatStage } from "@/hooks/useChat";
import { BlockRenderer } from "@/components/generative-ui/BlockRenderer";
import { AgentTrace } from "@/components/generative-ui/AgentTrace";
import ReactMarkdown from "react-markdown";

interface MessageBubbleProps {
  message: ChatMessage;
  isLatestStockOverview?: boolean;
}



function LiveStatusIndicator({ message }: { message: ChatMessage }) {
  const stage = message.stage;
  const trace = message.toolTrace;

  if (!message.isStreaming) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2">
      {/* Stage label */}
      {stage === "planning" && (
        <span
          className="text-[11px] px-2.5 py-1 rounded-md"
          style={{
            background: "var(--accent-muted)",
            color: "var(--accent)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Planning…
        </span>
      )}

      {/* Completed tool call chips */}
      {trace.map((call, i) => (
        <span
          key={i}
          className="text-[11px] px-2 py-0.5 rounded-md"
          style={{
            background: "var(--bg-panel-muted)",
            border: "0.5px solid var(--border)",
            color: "var(--text-secondary)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {call.tool} · {call.latency_ms}ms
        </span>
      ))}

      {/* "Writing response..." chip */}
      {stage === "responding" && (
        <span
          className="text-[11px] px-2.5 py-1 rounded-md"
          style={{
            background: "var(--accent-muted)",
            color: "var(--accent)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Writing response…
        </span>
      )}

      {/* Executing but no response yet — show active indicator after tool chips */}
      {stage === "executing" && (
        <span
          className="text-[11px] px-2.5 py-1 rounded-md"
          style={{
            background: "var(--accent-muted)",
            color: "var(--accent)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Fetching data…
        </span>
      )}
    </div>
  );
}

export function MessageBubble({ message, isLatestStockOverview }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [showTrace, setShowTrace] = useState(false);

  // Extract AgentTrace block from uiBlocks (it's appended by onDone)
  const agentTraceBlock = message.uiBlocks.find(
    (b: any) => b && typeof b === "object" && "component" in b && b.component === "AgentTrace"
  ) as { component: string; props: any } | undefined;

  // All other UI blocks (PriceChart, FilingExcerpt, etc.)
  const contentBlocks = message.uiBlocks.filter(
    (b: any) => !(b && typeof b === "object" && "component" in b && b.component === "AgentTrace")
  );

  if (isUser) {
    return (
      <div className="flex justify-end animate-slide-up" id={`message-${message.id}`}>
        <div
          className="px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
          style={{
            background: "var(--accent)",
            color: "#fff",
            borderRadius: "10px 10px 2px 10px",
            maxWidth: "70%",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start animate-slide-up" id={`message-${message.id}`}>
      <div
        className="px-5 py-4"
        style={{
          background: "var(--bg-panel)",
          border: "0.5px solid var(--border)",
          borderRadius: "10px 10px 10px 2px",
          maxWidth: "78%",
          color: "var(--text-primary)",
        }}
      >
        {/* Live status indicator (only while streaming) */}
        <LiveStatusIndicator message={message} />

        {/* Prose answer */}
        {message.content && (
          <div className="text-sm leading-relaxed whitespace-pre-wrap">
            <ReactMarkdown
              components={{
                h1: ({node, ...props}) => <h1 className="text-lg font-bold mt-4 mb-2" {...props} />,
                h2: ({node, ...props}) => <h2 className="text-base font-bold mt-4 mb-2" {...props} />,
                h3: ({node, ...props}) => <h3 className="text-sm font-semibold mt-4 mb-2" {...props} />,
                p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3" {...props} />,
                li: ({node, ...props}) => <li className="mb-1" {...props} />,
                strong: ({node, ...props}) => <strong className="font-semibold text-text-primary" {...props} />,
                em: ({node, ...props}) => <em className="italic" {...props} />,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* UI Blocks inline (PriceChart, FilingExcerpt) */}
        {contentBlocks.length > 0 && (
          <div className="mt-3 space-y-3">
            {contentBlocks.map((block, i) => (
              <BlockRenderer key={i} block={block} isLatestStockOverview={isLatestStockOverview} />
            ))}
          </div>
        )}

        {/* Show trace toggle */}
        {agentTraceBlock && !message.isStreaming && (
          <div className="mt-3">
            <button
              onClick={() => setShowTrace(!showTrace)}
              className="text-xs hover:underline transition-colors bg-transparent border-none p-0 cursor-pointer"
              style={{
                color: "var(--text-muted)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {showTrace ? "Hide trace ▴" : "Show trace ▾"}
            </button>
            {showTrace && (
              <div className="mt-2">
                <AgentTrace
                  toolCalls={agentTraceBlock.props.toolCalls}
                  totalLatencyMs={agentTraceBlock.props.totalLatencyMs}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
