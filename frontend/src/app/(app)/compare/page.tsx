"use client";

import { useState } from "react";
import { Search, X, Loader2 } from "lucide-react";

interface CompareResult {
  ticker: string;
  shortName: string;
  currentPrice: number | null;
  marketCap: number | null;
  trailingPE: number | null;
  forwardPE: number | null;
  revenueGrowth: number | null;
  returnOnEquity: number | null;
  debtToEquity: number | null;
  dividendYield: number | null;
  profitMargins: number | null;
}

interface CompareResponse {
  results: CompareResult[];
  failed: { ticker: string; error: string }[];
}

export default function ComparePage() {
  const [tickers, setTickers] = useState<string[]>(["AAPL", "MSFT", "GOOGL"]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CompareResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchComparison = async (tickersToFetch: string[]) => {
    if (tickersToFetch.length === 0) {
      setData([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/v1/compare?tickers=${tickersToFetch.join(",")}`);
      if (!res.ok) throw new Error("Failed to fetch comparison data");
      const json: CompareResponse = await res.json();
      setData(json.results);
      if (json.failed.length > 0) {
        setError(`Failed to fetch data for: ${json.failed.map(f => f.ticker).join(", ")}`);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTicker = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    const newTicker = inputValue.trim().toUpperCase();
    if (tickers.includes(newTicker)) {
      setInputValue("");
      return;
    }
    if (tickers.length >= 5) {
      setError("Maximum 5 tickers allowed for comparison.");
      return;
    }
    const newTickers = [...tickers, newTicker];
    setTickers(newTickers);
    setInputValue("");
    fetchComparison(newTickers);
  };

  const handleRemoveTicker = (tickerToRemove: string) => {
    const newTickers = tickers.filter(t => t !== tickerToRemove);
    setTickers(newTickers);
    fetchComparison(newTickers);
  };

  const formatValue = (val: number | null, format: "currency" | "percent" | "compact" | "number" = "number") => {
    if (val === null || val === undefined) return "—";
    
    switch (format) {
      case "currency":
        return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);
      case "percent":
        return `${(val * 100).toFixed(2)}%`;
      case "compact":
        return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(val);
      default:
        return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(val);
    }
  };

  // Find max/min for highlighting
  const getHighlightClass = (metric: keyof CompareResult, value: number | null, isHigherBetter: boolean) => {
    if (value === null || data.length < 2) return "";
    
    const validValues = data.map(d => d[metric] as number).filter(v => v !== null && v !== undefined);
    if (validValues.length < 2) return "";
    
    const max = Math.max(...validValues);
    const min = Math.min(...validValues);
    
    if (value === max) return isHigherBetter ? "text-gain font-bold" : "text-loss font-bold";
    if (value === min) return isHigherBetter ? "text-loss font-bold" : "text-gain font-bold";
    return "";
  };

  return (
    <div className="max-w-6xl mx-auto p-8 animate-fade-in h-full flex flex-col">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-display font-medium text-text-primary">Peer Comparison</h1>
        
        <form onSubmit={handleAddTicker} className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input 
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder="Add ticker..."
              className="pl-9 pr-4 py-2 bg-panel border border-border rounded-lg text-sm focus:outline-none focus:border-accent w-48"
              disabled={tickers.length >= 5 || loading}
            />
          </div>
          <button 
            type="submit" 
            disabled={!inputValue.trim() || tickers.length >= 5 || loading}
            className="btn-primary px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            Add
          </button>
        </form>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {tickers.map(ticker => (
          <div key={ticker} className="flex items-center gap-1.5 bg-panel border border-border px-3 py-1.5 rounded-full text-sm font-medium">
            <span>{ticker}</span>
            <button 
              onClick={() => handleRemoveTicker(ticker)}
              className="text-text-muted hover:text-loss transition-colors rounded-full hover:bg-loss-muted p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {tickers.length === 0 && (
          <div className="text-sm text-text-muted">No tickers selected. Add some above.</div>
        )}
      </div>

      {error && (
        <div className="bg-loss-muted text-loss px-4 py-3 rounded-lg text-sm mb-6 font-medium">
          {error}
        </div>
      )}

      {tickers.length > 0 && data.length === 0 && !loading && (
        <button 
          onClick={() => fetchComparison(tickers)}
          className="btn-primary self-start px-6 py-2 rounded-lg text-sm"
        >
          Compare Selected ({tickers.length})
        </button>
      )}

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center text-text-muted gap-3">
          <Loader2 className="w-8 h-8 animate-spin" />
          <p className="text-sm">Fetching real-time financials...</p>
        </div>
      ) : data.length > 0 ? (
        <div className="bg-panel border border-border rounded-xl shadow-sm overflow-hidden flex-1 overflow-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-page/50 border-b border-border sticky top-0 z-10">
              <tr>
                <th className="px-6 py-4 font-medium text-text-secondary uppercase text-xs tracking-wider">Metric</th>
                {data.map(d => (
                  <th key={d.ticker} className="px-6 py-4 font-bold text-text-primary">
                    <div className="text-lg">{d.ticker}</div>
                    <div className="text-xs font-normal text-text-muted truncate w-32">{d.shortName}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Current Price</td>
                {data.map(d => (
                  <td key={d.ticker} className="px-6 py-4 font-mono">{formatValue(d.currentPrice, "currency")}</td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Market Cap</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('marketCap', d.marketCap, true)}`}>
                    {formatValue(d.marketCap, "compact")}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">P/E (Trailing)</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('trailingPE', d.trailingPE, false)}`}>
                    {formatValue(d.trailingPE)}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">P/E (Forward)</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('forwardPE', d.forwardPE, false)}`}>
                    {formatValue(d.forwardPE)}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Revenue Growth (YoY)</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('revenueGrowth', d.revenueGrowth, true)}`}>
                    {formatValue(d.revenueGrowth, "percent")}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Profit Margin</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('profitMargins', d.profitMargins, true)}`}>
                    {formatValue(d.profitMargins, "percent")}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Return on Equity</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('returnOnEquity', d.returnOnEquity, true)}`}>
                    {formatValue(d.returnOnEquity, "percent")}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Debt to Equity</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('debtToEquity', d.debtToEquity, false)}`}>
                    {formatValue(d.debtToEquity ? d.debtToEquity / 100 : null, "percent")}
                  </td>
                ))}
              </tr>
              <tr className="hover:bg-page/30 transition-colors">
                <td className="px-6 py-4 font-medium text-text-secondary">Dividend Yield</td>
                {data.map(d => (
                  <td key={d.ticker} className={`px-6 py-4 font-mono ${getHighlightClass('dividendYield', d.dividendYield, true)}`}>
                    {formatValue(d.dividendYield, "percent")}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
