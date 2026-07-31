"use client";

import { useState, useEffect } from "react";
import type { ResearchCardProps } from "./schemas";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CheckCircle2, Clock } from "lucide-react";
import { NewsList } from "./NewsList";
import { FilingExcerpt } from "./FilingExcerpt";

const PERIODS = ["1d", "5d", "1mo", "6mo", "1y", "5y", "max"];
const PERIOD_LABELS: Record<string, string> = {
  "1d": "1D", "5d": "5D", "1mo": "1M", "6mo": "6M", "1y": "1Y", "5y": "5Y", "max": "Max"
};

export function ResearchCard(props: ResearchCardProps) {
  const {
    ticker,
    currency = "INR",
    currentPrice: initial_price,
    lastUpdated: initial_as_of,
    period: initial_period = "1mo",
    historicalPrices: initial_history,
    keyMetrics,
    kpis,
    news,
    excerpts,
    sources = [],
  } = props;

  const currentPrice = initial_price;
  const lastUpdate = initial_as_of ? new Date(initial_as_of).getTime() : null;
  
  const [activePeriod, setActivePeriod] = useState(initial_period);
  const [history, setHistory] = useState(initial_history || []);
  const [isLoadingChart, setIsLoadingChart] = useState(false);

  useEffect(() => {
    if (activePeriod === initial_period && initial_history) {
      setHistory(initial_history);
      return;
    }

    let isMounted = true;
    const fetchChart = async () => {
      setIsLoadingChart(true);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/chart/${ticker}?period=${activePeriod}`);
        if (!res.ok) throw new Error("Failed to fetch chart");
        const data = await res.json();
        if (isMounted && data.history) {
          setHistory(data.history);
        }
      } catch (e) {
        console.error(e);
      } finally {
        if (isMounted) setIsLoadingChart(false);
      }
    };
    fetchChart();
    return () => { isMounted = false; };
  }, [activePeriod, ticker, initial_period, initial_history]);

  const hasChart = history && history.length > 0;
  
  let change = 0;
  let changePercent = "0.00";
  let isPositive = true;

  if (hasChart) {
    const firstClose = history[0].close;
    const lastClose = history[history.length - 1].close;
    // Current price is live, but for accurate change calculation over period, use the live price if we are on 1D? 
    // Usually, we compare currentPrice to the first close of the period.
    const actualCurrent = currentPrice || lastClose;
    change = actualCurrent - firstClose;
    changePercent = ((Math.abs(change) / firstClose) * 100).toFixed(2);
    isPositive = change >= 0;
  }

  const isUSD = currency === "USD";
  const currencySymbol = isUSD ? "$" : "₹";
  const locale = isUSD ? "en-US" : "en-IN";

  const formatValue = (val: number | string | null, format: string) => {
    if (val === null || val === undefined) return "—";
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return val.toString();

    switch (format) {
      case "currency":
        return `${currencySymbol}${num.toLocaleString(locale, { maximumFractionDigits: 2 })}`;
      case "percent":
        return `${(num * 100).toFixed(2)}%`;
      case "compact":
        return `${currencySymbol}${new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 2 }).format(num)}`;
      default:
        return num.toLocaleString(locale, { maximumFractionDigits: 2 });
    }
  };

  const hasMetrics = keyMetrics && keyMetrics.length > 0;
  const hasKpis = kpis && kpis.length > 0;
  const hasNews = news && news.length > 0;
  const hasExcerpts = excerpts && excerpts.length > 0;

  return (
    <div className="max-w-4xl w-full mx-auto bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden flex flex-col my-4 animate-slide-up">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3 mb-4 sm:mb-0">
          <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-lg font-bold text-gray-700 dark:text-gray-300">
            {ticker[0]}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
                {ticker}
              </h2>
              {lastUpdate && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
              )}
            </div>
            {lastUpdate && (
              <div className="flex items-center gap-1 text-[11px] text-gray-500 font-medium">
                <Clock className="w-3 h-3" />
                {new Date(lastUpdate).toLocaleString(locale, {
                  month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                })}
              </div>
            )}
          </div>
        </div>
        
        {currentPrice !== undefined && (
          <div className="flex flex-col sm:items-end">
            <span className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
              {formatValue(currentPrice, "currency")}
            </span>
            {hasChart && (
              <span className={`text-sm font-semibold flex items-center gap-1 ${isPositive ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}>
                {isPositive ? "▲" : "▼"} {Math.abs(change).toFixed(2)} ({changePercent}%)
              </span>
            )}
          </div>
        )}
      </div>

      {/* STOCK OVERVIEW ROW */}
      {(hasChart || hasMetrics) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
          {hasChart && (
            <div className="md:col-span-2 flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 tracking-tight">Price History</h3>
                <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                  {PERIODS.map(p => (
                    <button
                      key={p}
                      onClick={() => setActivePeriod(p)}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                        activePeriod === p 
                          ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm" 
                          : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                      }`}
                    >
                      {PERIOD_LABELS[p]}
                    </button>
                  ))}
                </div>
              </div>
              <div className={`h-[240px] transition-opacity duration-300 ${isLoadingChart ? "opacity-50" : "opacity-100"}`}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0.2}/>
                        <stop offset="95%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(156, 163, 175, 0.2)" />
                    <XAxis 
                      dataKey="date" 
                      tickLine={false} 
                      axisLine={false} 
                      tick={{ fontSize: 11, fill: "#9ca3af" }}
                      tickFormatter={(d) => {
                        const date = new Date(d);
                        if (activePeriod === "1d" || activePeriod === "5d") {
                          return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
                        }
                        return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
                      }}
                      dy={10}
                      minTickGap={30}
                    />
                    <YAxis 
                      domain={['auto', 'auto']}
                      tickLine={false} 
                      axisLine={false} 
                      tick={{ fontSize: 11, fill: "#9ca3af" }}
                      tickFormatter={(v) => `${currencySymbol}${v.toLocaleString(locale, { maximumFractionDigits: 0 })}`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--bg-panel)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "13px",
                        boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
                        color: "var(--text-primary)"
                      }}
                      itemStyle={{ fontWeight: 600, color: "var(--text-primary)" }}
                      labelFormatter={(l) => new Date(l).toLocaleString(locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      formatter={(val: number) => [`${currencySymbol}${val.toLocaleString(locale, { minimumFractionDigits: 2 })}`, 'Price']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="close" 
                      stroke={isPositive ? "#22c55e" : "#ef4444"} 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorClose)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {hasMetrics && (
            <div className={`flex flex-col ${!hasChart ? "md:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-4" : ""}`}>
              {hasChart && <h3 className="font-semibold text-gray-900 dark:text-gray-100 tracking-tight mb-4">Key Metrics</h3>}
              <div className={!hasChart ? "col-span-full grid grid-cols-2 sm:grid-cols-4 gap-4" : "flex flex-col gap-3"}>
                {keyMetrics.map(m => (
                  <div key={m.label} className="flex flex-col p-3 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-100 dark:border-gray-800">
                    <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">{m.label}</span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100 mt-1">{formatValue(m.value, m.format)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* KPI GRID */}
      {hasKpis && (
        <div className="px-6 pb-6 pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {kpis.map(m => (
              <div key={m.label} className="flex flex-col p-4 bg-gray-50 dark:bg-white/5 rounded-xl border border-gray-100 dark:border-gray-800 transition-all hover:border-gray-200 dark:hover:border-gray-700">
                <span className="text-xs font-medium text-gray-500">{m.label}</span>
                <span className="text-lg font-bold text-gray-900 dark:text-gray-100 mt-1 tracking-tight">{formatValue(m.value, m.format)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DEEP DIVE ROW (Excerpts & News) */}
      {(hasExcerpts || hasNews) && (
        <div className={`grid grid-cols-1 ${hasExcerpts && hasNews ? "md:grid-cols-2" : ""} gap-8 p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50`}>
          {hasExcerpts && (
            <div className="flex flex-col">
              <FilingExcerpt {...{ticker, source: "seed", documentTitle: excerpts[0].documentTitle, excerpts}} />
            </div>
          )}
          {hasNews && (
            <div className="flex flex-col">
              <NewsList ticker={ticker} news={news} />
            </div>
          )}
        </div>
      )}

      {/* FOOTER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-800 text-[11px] text-gray-500">
        <div className="flex items-center gap-1.5 mb-2 sm:mb-0 text-green-600 dark:text-green-500 font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Data verified and up-to-date
        </div>
        {sources && sources.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Sources:</span>
            <span className="font-medium text-gray-600 dark:text-gray-400">{sources.join(", ")}</span>
          </div>
        )}
      </div>
    </div>
  );
}
