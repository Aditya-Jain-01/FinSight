"use client";

import { AgentTraceProps } from "./schemas";

export function AgentTrace({ toolCalls, totalLatencyMs }: AgentTraceProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="space-y-3 animate-slide-up" id="agent-trace-panel">
      {toolCalls.map((call, i) => (
        <div
          key={i}
          className="rounded p-4 text-xs"
          style={{
            background: "var(--bg-panel)",
            border: "1px solid var(--border)",
          }}
        >
          <div className="flex items-center justify-between mb-3 pb-2"
               style={{ borderTop: "1px dashed var(--border-strong)", paddingTop: "8px" }}>
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: call.error ? "var(--loss)" : "var(--gain)" }}
              />
              <span style={{ color: "var(--text-primary)", fontWeight: 500, fontFamily: "var(--font-body)" }}>
                {call.tool}
              </span>
            </div>
            <span
              className="px-1.5 py-0.5 rounded text-[10px]"
              style={{
                fontFamily: "var(--font-mono)",
                fontVariantNumeric: "tabular-nums",
                background: call.latency_ms > 2000 ? "var(--loss-muted)" : "var(--bg-panel-muted)",
                color: call.latency_ms > 2000 ? "var(--loss)" : "var(--text-secondary)",
                border: call.latency_ms > 2000 ? "none" : "1px solid var(--border)",
              }}
            >
              {call.latency_ms}ms
            </span>
          </div>

          {/* Args */}
          <div className="mb-3">
            <span className="text-[10px] uppercase tracking-wider"
                  style={{ color: "var(--text-muted)", fontFamily: "var(--font-body)", fontWeight: 500 }}>
              Args
            </span>
            <pre
              className="mt-1 overflow-x-auto whitespace-pre-wrap break-all p-2 rounded"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--text-secondary)",
                background: "var(--bg-panel-muted)",
                border: "1px solid var(--border)",
              }}
            >
              {JSON.stringify(call.args, null, 2)}
            </pre>
          </div>

          {/* Result */}
          {call.error ? (
            <div
              className="p-2 rounded"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--loss)",
                background: "var(--loss-muted)",
                border: "1px solid var(--loss)",
                borderColor: "rgba(162, 62, 54, 0.2)",
              }}
            >
              Error: {call.error}
            </div>
          ) : (
            <div>
              <span className="text-[10px] uppercase tracking-wider"
                    style={{ color: "var(--text-muted)", fontFamily: "var(--font-body)", fontWeight: 500 }}>
                Result
              </span>
              <pre
                className="mt-1 overflow-x-auto whitespace-pre-wrap break-all max-h-32 overflow-y-auto p-2 rounded"
                style={{
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-secondary)",
                  background: "var(--bg-panel-muted)",
                  border: "1px solid var(--border)",
                }}
              >
                {JSON.stringify(call.raw_result, null, 2).slice(0, 500)}
                {JSON.stringify(call.raw_result, null, 2).length > 500 ? "…" : ""}
              </pre>
            </div>
          )}
        </div>
      ))}
      <div
        className="text-[10px] text-right mt-1"
        style={{
          color: "var(--text-muted)",
          fontFamily: "var(--font-mono)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        Total: {totalLatencyMs}ms
      </div>
    </div>
  );
}
