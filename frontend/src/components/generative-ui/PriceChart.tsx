"use client";

import { PriceChartProps } from "./schemas";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export function PriceChart({ ticker, currency = "INR", current_price: initial_price, as_of: initial_as_of, period, history }: PriceChartProps) {
  const currentPrice = initial_price;
  const lastUpdate = initial_as_of ? new Date(initial_as_of).getTime() : null;
  if (!history || history.length === 0) return null;

  const firstClose = history[0].close;
  const lastClose = history[history.length - 1].close;
  const change = lastClose - firstClose;
  const changePercent = ((Math.abs(change) / firstClose) * 100).toFixed(2);
  const isPositive = change >= 0;

  const isUSD = currency === "USD";
  const currencySymbol = isUSD ? "$" : "₹";
  const locale = isUSD ? "en-US" : "en-IN";

  const formatPrice = (val: number) => {
    return `${currencySymbol}${val.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="bg-panel border border-border rounded-lg shadow-sm p-5 animate-slide-up my-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="figure text-xs font-medium px-2 py-0.5 bg-panel-muted border border-border text-text-primary rounded">
              {ticker}
            </span>
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">{period}</span>
          </div>
          {lastUpdate && (
            <div className="text-[10px] text-text-muted mb-3 font-mono">
              As of: {new Date(lastUpdate).toLocaleString(locale, {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short"
              })}
            </div>
          )}
          <div className="flex items-baseline gap-3">
            <span className="figure text-3xl font-semibold text-text-primary tracking-tight transition-colors duration-300">
              {formatPrice(currentPrice)}
            </span>
            <span
              className={`figure text-sm font-medium ${
                isPositive ? "text-gain" : "text-loss"
              }`}
            >
              {isPositive ? "▲" : "▼"} {Math.abs(change).toFixed(2)} ({changePercent}%)
            </span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48 ledger-rule">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 12, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid
              strokeDasharray="2 2"
              stroke="var(--border)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(d: string) => {
                const date = new Date(d);
                return `${date.getDate()}/${date.getMonth() + 1}`;
              }}
              interval="preserveStartEnd"
              dy={10}
            />
            <YAxis
              tick={{ fill: "var(--text-secondary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={false}
              width={60}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => `${currencySymbol}${v.toLocaleString(locale, { maximumFractionDigits: 0 })}`}
              dx={-10}
            />
            <Tooltip
              contentStyle={{
                background: "var(--bg-panel)",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                fontSize: "12px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
                fontFamily: "var(--font-mono)",
                color: "var(--text-primary)"
              }}
              itemStyle={{ color: "var(--text-primary)", fontWeight: 500 }}
              formatter={(value: number) => [
                formatPrice(value),
                "Close",
              ]}
              labelFormatter={(label: string) =>
                new Date(label).toLocaleDateString(locale, {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })
              }
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke={isPositive ? "var(--gain)" : "var(--loss)"}
              strokeWidth={2}
              fill="transparent"
              dot={false}
              activeDot={{
                r: 4,
                fill: isPositive ? "var(--gain)" : "var(--loss)",
                stroke: "var(--bg-panel)",
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
