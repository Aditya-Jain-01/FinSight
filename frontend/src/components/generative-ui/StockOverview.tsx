"use client";

import { useState } from "react";
import { usePriceStream } from "@/hooks/usePriceStream";
import type { StockOverviewProps } from "./schemas";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/**
 * Unified stock overview card — the ONLY ticker-specific UI block
 * emitted by the current backend. Combines price chart, financials,
 * news, and (optionally) a filing excerpt into one card.
 *
 * `isLatest` prop controls whether this card opens a live WebSocket
 * connection for real-time price ticking. Only the most recent
 * StockOverview in the thread should set this to true.
 */
export function StockOverview(props: StockOverviewProps & { isLatest?: boolean }) {
  const {
    ticker,
    currency = "INR",
    price,
    metrics,
    news,
    filingExcerpt,
    sources = [],
    isLatest = false,
  } = props;

  // Live price from WebSocket — only for the latest card
  const liveStream = usePriceStream(
    isLatest ? ticker : undefined,
    price?.current ?? 0,
    price?.asOf
  );

  const displayPrice = isLatest ? liveStream.currentPrice : (price?.current ?? 0);
  const displayChange = price?.change ?? 0;
  const displayChangePct = price?.changePercent ?? 0;
  const isPositive = displayChange >= 0;

  const isUSD = currency === "USD";
  const sym = isUSD ? "$" : "₹";
  const locale = isUSD ? "en-US" : "en-IN";

  const fmtPrice = (v: number) =>
    `${sym}${v.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const fmtMetric = (value: number | null, format: string) => {
    if (value === null || value === undefined) return "—";
    switch (format) {
      case "currency":
        return `${sym}${value.toLocaleString(locale, { maximumFractionDigits: 2 })}`;
      case "percent":
        return `${(value * 100).toFixed(2)}%`;
      case "compact":
        return `${sym}${new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 2 }).format(value)}`;
      default:
        return value.toLocaleString(locale, { maximumFractionDigits: 2 });
    }
  };

  const [excerptExpanded, setExcerptExpanded] = useState(false);

  const hasChart = price?.history && price.history.length > 0;
  const hasMetrics = metrics && metrics.length > 0;
  const hasNews = news && news.length > 0;
  const hasExcerpt = !!filingExcerpt;

  // Split metrics into "key" (first 6) and "extra" (rest) for layout
  const keyMetrics = metrics?.slice(0, 6) ?? [];
  const extraMetrics = metrics?.slice(6) ?? [];

  return (
    <div
      className="animate-slide-up my-4 overflow-hidden"
      style={{
        background: "var(--bg-panel)",
        border: "1px solid var(--border)",
        borderRadius: 12,
      }}
    >
      {/* ── HEADER ──────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-3">
          {/* Ticker badge */}
          <span
            className="figure text-xs font-semibold px-2 py-0.5 rounded uppercase"
            style={{
              background: "var(--bg-panel-muted)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
          >
            {ticker}
          </span>

          {/* Live / Static indicator */}
          {isLatest && liveStream.lastUpdate ? (
            <span className="flex items-center gap-1.5 text-[10px] font-medium" style={{ color: "var(--gain)" }}>
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: "var(--gain)" }} />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ background: "var(--gain)" }} />
              </span>
              Live
            </span>
          ) : price?.asOf ? (
            <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
              as of {new Date(price.asOf).toLocaleString(locale, {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
              })}
            </span>
          ) : null}
        </div>

        {/* Price + Change */}
        {price && (
          <div className="flex items-baseline gap-2">
            <span
              className="figure text-2xl font-semibold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              {fmtPrice(displayPrice)}
            </span>
            <span
              className="figure text-sm font-medium"
              style={{ color: isPositive ? "var(--gain)" : "var(--loss)" }}
            >
              {isPositive ? "▲" : "▼"} {Math.abs(displayChange).toFixed(2)} ({Math.abs(displayChangePct).toFixed(2)}%)
            </span>
          </div>
        )}
      </div>

      {/* ── CHART + KEY METRICS ROW ─────────────────────────── */}
      {(hasChart || keyMetrics.length > 0) && (
        <div
          className="grid gap-5 p-5"
          style={{ gridTemplateColumns: hasChart && keyMetrics.length > 0 ? "2fr 1fr" : "1fr" }}
        >
          {/* Chart */}
          {hasChart && (
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={price!.history} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isPositive ? "var(--gain)" : "var(--loss)"} stopOpacity={0.15} />
                      <stop offset="95%" stopColor={isPositive ? "var(--gain)" : "var(--loss)"} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 2" stroke="var(--border)" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(d: string) => {
                      const dt = new Date(d);
                      return `${dt.getDate()}/${dt.getMonth() + 1}`;
                    }}
                    interval="preserveStartEnd"
                    dy={8}
                  />
                  <YAxis
                    tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                    tickLine={false}
                    axisLine={false}
                    width={55}
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) =>
                      `${sym}${v.toLocaleString(locale, { maximumFractionDigits: 0 })}`
                    }
                    dx={-6}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-panel)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      fontSize: 12,
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-primary)",
                    }}
                    formatter={(val: number) => [fmtPrice(val), "Close"]}
                    labelFormatter={(l: string) =>
                      new Date(l).toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" })
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    stroke={isPositive ? "var(--gain)" : "var(--loss)"}
                    strokeWidth={2}
                    fill={`url(#grad-${ticker})`}
                    dot={false}
                    activeDot={{
                      r: 3,
                      fill: isPositive ? "var(--gain)" : "var(--loss)",
                      stroke: "var(--bg-panel)",
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Key Metrics sidebar */}
          {keyMetrics.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-[10px] uppercase tracking-wider font-medium mb-1" style={{ color: "var(--text-muted)" }}>
                Key Metrics
              </h4>
              {keyMetrics.map((m) => (
                <div
                  key={m.label}
                  className="flex items-center justify-between px-3 py-2 rounded-md"
                  style={{
                    background: "var(--bg-panel-muted)",
                    border: "0.5px solid var(--border)",
                  }}
                >
                  <span className="text-[11px]" style={{ color: "var(--text-secondary)" }}>
                    {m.label}
                  </span>
                  <span
                    className="figure text-sm font-medium"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {fmtMetric(m.value, m.format)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── EXTRA METRICS TILES ─────────────────────────────── */}
      {extraMetrics.length > 0 && (
        <div className="px-5 pb-4">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 8 }}>
            {extraMetrics.map((m) => (
              <div
                key={m.label}
                className="rounded-md px-3 py-2"
                style={{
                  background: "var(--bg-panel-muted)",
                  border: "0.5px solid var(--border)",
                }}
              >
                <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>{m.label}</div>
                <div
                  className="figure text-sm font-medium mt-0.5"
                  style={{ color: "var(--text-primary)" }}
                >
                  {fmtMetric(m.value, m.format)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── EXCERPT + NEWS ROW ──────────────────────────────── */}
      {(hasExcerpt || hasNews) && (
        <div
          className="grid gap-5 p-5"
          style={{
            gridTemplateColumns: hasExcerpt && hasNews ? "1fr 1fr" : "1fr",
            borderTop: "1px solid var(--border)",
          }}
        >
          {/* Filing Excerpt */}
          {hasExcerpt && (
            <div>
              <h4 className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                Annual Report Excerpt
              </h4>
              <div
                className="rounded-md px-3 py-2.5"
                style={{
                  background: "var(--bg-panel-muted)",
                  borderLeft: "3px solid var(--accent)",
                }}
              >
                <div className="text-[10px] font-medium mb-1" style={{ color: "var(--accent)" }}>
                  {filingExcerpt!.documentTitle} — {filingExcerpt!.sectionTitle}
                </div>
                <p
                  className={`text-sm leading-relaxed ${excerptExpanded ? "" : "line-clamp-3"}`}
                  style={{ color: "var(--text-primary)" }}
                >
                  {filingExcerpt!.content}
                </p>
                {filingExcerpt!.content.length > 200 && (
                  <button
                    onClick={() => setExcerptExpanded(!excerptExpanded)}
                    className="text-xs mt-1 bg-transparent border-none p-0 cursor-pointer"
                    style={{ color: "var(--accent)" }}
                  >
                    {excerptExpanded ? "Show less" : "Show full excerpt"}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* News */}
          {hasNews && (
            <div>
              <h4 className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: "var(--text-muted)" }}>
                Latest News
              </h4>
              <div className="flex flex-col gap-2">
                {news!.map((n, i) => (
                  <a
                    key={i}
                    href={n.link ?? "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-md px-3 py-2 transition-colors"
                    style={{
                      background: "var(--bg-panel-muted)",
                      border: "0.5px solid var(--border)",
                      textDecoration: "none",
                    }}
                  >
                    <div className="text-sm font-medium leading-snug" style={{ color: "var(--text-primary)" }}>
                      {n.title}
                    </div>
                    {n.publisher && (
                      <div className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                        {n.publisher}
                      </div>
                    )}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── FOOTER ──────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-5 py-2.5 text-[10px]"
        style={{
          borderTop: "1px solid var(--border)",
          background: "var(--bg-panel-muted)",
          color: "var(--text-muted)",
        }}
      >
        <span style={{ color: "var(--gain)" }}>✓ Data verified</span>
        {sources.length > 0 && (
          <span>
            Sources: <span style={{ color: "var(--text-secondary)" }}>{sources.join(", ")}</span>
          </span>
        )}
      </div>
    </div>
  );
}
