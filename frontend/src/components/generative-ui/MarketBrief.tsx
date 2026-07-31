"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Newspaper, Loader2, ArrowUpRight, ArrowDownRight, Clock } from "lucide-react";
import { PriceChart } from "./PriceChart";

interface IndexData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  time: number;
  market: "US" | "IN";
}

interface MarketDataSubset {
  gainers: IndexData[];
  losers: IndexData[];
  news: NewsItem[];
}

interface MarketBriefData {
  indices: IndexData[];
  us: MarketDataSubset;
  in: MarketDataSubset;
}

const formatRelativeTime = (timestamp: number) => {
  if (!timestamp || timestamp === 0) return "Recently";
  const now = Math.floor(Date.now() / 1000);
  const diff = Math.max(0, now - timestamp);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

export function MarketBrief() {
  const [data, setData] = useState<MarketBriefData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const [selectedMarket, setSelectedMarket] = useState<"US" | "IN">("US");
  const [selectedIndex, setSelectedIndex] = useState<string>("^GSPC");
  
  const [chartHistory, setChartHistory] = useState<any[] | null>(null);
  const [chartLoading, setChartLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/api/v1/market/brief`);
        if (!res.ok) throw new Error("Failed to fetch market brief");
        const json = await res.json();
        setData(json);
        
        const now = new Date();
        setLastUpdated(now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }));
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    const fetchChart = async () => {
      if (!selectedIndex) return;
      setChartLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/api/v1/chart/${selectedIndex}?period=1mo`);
        if (res.ok) {
          const json = await res.json();
          setChartHistory(json.history);
        } else {
          setChartHistory(null);
        }
      } catch (err) {
        setChartHistory(null);
      } finally {
        setChartLoading(false);
      }
    };
    fetchChart();
  }, [selectedIndex]);

  if (loading) {
    return (
      <div className="bg-panel border border-border rounded-xl p-6 w-full max-w-3xl flex flex-col items-center justify-center min-h-[200px]">
        <Loader2 className="w-8 h-8 animate-spin text-text-muted mb-4" />
        <div className="text-text-secondary text-sm">Fetching latest market data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-loss-muted text-loss border border-loss/20 rounded-xl p-4 w-full max-w-3xl text-sm">
        Failed to load market brief: {error}
      </div>
    );
  }

  const formatPrice = (val: number) => 
    new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(val);

  const usIndices = data.indices.filter(idx => ["^GSPC", "^IXIC", "^DJI"].includes(idx.symbol));
  const inIndices = data.indices.filter(idx => ["^NSEI", "^BSESN"].includes(idx.symbol));

  const activeIndices = selectedMarket === "US" ? usIndices : inIndices;
  const activeData = selectedMarket === "US" ? data.us : data.in;

  const handleMarketChange = (market: "US" | "IN") => {
    setSelectedMarket(market);
    if (market === "US") setSelectedIndex("^GSPC");
    else setSelectedIndex("^NSEI");
  };

  const selectedIndexData = activeIndices.find(i => i.symbol === selectedIndex);

  const IndexTile = ({ idx }: { idx: IndexData }) => {
    const isSelected = idx.symbol === selectedIndex;
    return (
      <button 
        onClick={() => setSelectedIndex(idx.symbol)}
        className={`flex flex-col text-left transition-all p-3 rounded-lg border flex-1 min-w-0 ${
          isSelected 
            ? "bg-page border-border-strong ring-1 ring-border-strong shadow-sm" 
            : "bg-transparent border-transparent hover:bg-page/50 cursor-pointer"
        }`}
      >
        <div className="text-xs font-medium text-text-secondary truncate w-full">{idx.name}</div>
        <div className="font-mono text-sm font-bold text-text-primary mt-1">{formatPrice(idx.price)}</div>
        <div className={`font-mono flex items-center gap-1 text-[11px] mt-0.5 font-medium ${idx.change >= 0 ? "text-gain" : "text-loss"}`}>
          {idx.change >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {idx.change_percent.toFixed(2)}%
        </div>
      </button>
    );
  };

  return (
    <div className="bg-panel border border-border rounded-xl w-full max-w-3xl overflow-hidden animate-fade-in shadow-sm">
      {/* Header */}
      <div className="bg-page border-b border-border px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-lg font-display font-bold text-text-primary flex items-center gap-3">
          Global Market Brief
          
          <div className="flex bg-panel-muted p-1 rounded-md border border-border ml-2">
            <button
              onClick={() => handleMarketChange("US")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                selectedMarket === "US" 
                  ? "bg-accent text-panel shadow-sm" 
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              US Markets
            </button>
            <button
              onClick={() => handleMarketChange("IN")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                selectedMarket === "IN" 
                  ? "bg-accent text-panel shadow-sm" 
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              Indian Markets
            </button>
          </div>
        </h2>
        
        {lastUpdated && (
          <div className="flex items-center gap-1.5 text-xs font-mono text-text-secondary">
            <Clock className="w-3.5 h-3.5" />
            As of {lastUpdated}
          </div>
        )}
      </div>

      <div className="p-6">
        {/* Indices Tiles */}
        <div className="flex flex-row gap-2 mb-4 overflow-x-auto pb-2">
          {activeIndices.map(idx => <IndexTile key={idx.symbol} idx={idx} />)}
        </div>

        {/* Selected Index Chart */}
        {selectedIndexData && (
          <div className="mb-10 min-h-[220px]">
            {chartLoading ? (
              <div className="bg-panel border border-border rounded-lg shadow-sm p-5 h-full flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
              </div>
            ) : chartHistory && chartHistory.length > 0 ? (
              <PriceChart 
                ticker={selectedIndexData.name} 
                currency={selectedMarket === "US" ? "USD" : "INR"} 
                current_price={selectedIndexData.price} 
                period="1M" 
                history={chartHistory} 
              />
            ) : (
              <div className="bg-panel border border-border rounded-lg shadow-sm p-5 h-[220px] flex items-center justify-center text-sm text-text-muted italic">
                Chart data unavailable
              </div>
            )}
          </div>
        )}

        {/* Top Movers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
          <div>
            <h3 className="text-sm font-display font-medium text-text-primary mb-4 flex items-center gap-2 border-b border-border pb-2">
              <TrendingUp className="w-4 h-4 text-gain" /> Top Movers (Gainers)
            </h3>
            <div className="space-y-3">
              {activeData.gainers.map(g => (
                <div key={g.symbol} className="flex items-center justify-between group">
                  <div 
                    className="font-medium text-sm text-text-secondary truncate pr-4 group-hover:text-text-primary transition-colors"
                    title={g.name}
                  >
                    {g.name}
                  </div>
                  <div className="text-gain text-sm font-mono font-medium shrink-0">+{g.change_percent.toFixed(2)}%</div>
                </div>
              ))}
              {activeData.gainers.length === 0 && (
                <div className="text-sm text-text-muted italic">No data available</div>
              )}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-display font-medium text-text-primary mb-4 flex items-center gap-2 border-b border-border pb-2">
              <TrendingDown className="w-4 h-4 text-loss" /> Top Movers (Losers)
            </h3>
            <div className="space-y-3">
              {activeData.losers.map(l => (
                <div key={l.symbol} className="flex items-center justify-between group">
                  <div 
                    className="font-medium text-sm text-text-secondary truncate pr-4 group-hover:text-text-primary transition-colors"
                    title={l.name}
                  >
                    {l.name}
                  </div>
                  <div className="text-loss text-sm font-mono font-medium shrink-0">{l.change_percent.toFixed(2)}%</div>
                </div>
              ))}
              {activeData.losers.length === 0 && (
                <div className="text-sm text-text-muted italic">No data available</div>
              )}
            </div>
          </div>
        </div>

        {/* Market Headlines */}
        <div>
          <h3 className="text-sm font-display font-medium text-text-primary mb-4 flex items-center gap-2 border-b border-border pb-2">
            <Newspaper className="w-4 h-4 text-text-secondary" /> Market Headlines
          </h3>
          {activeData.news.length > 0 ? (
            <div className="space-y-4">
              {activeData.news.map((item, i) => (
                <a 
                  key={i} 
                  href={item.link} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="block group !text-text-primary hover:!text-text-secondary transition-colors"
                  style={{ textDecoration: 'none' }}
                >
                  <div className="text-sm font-medium">
                    {item.title}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-text-muted mt-1.5 font-medium">
                    <span className="uppercase tracking-wide">{item.publisher || "News"}</span>
                    <span>•</span>
                    <span className="font-mono">{formatRelativeTime(item.time)}</span>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <div className="text-sm text-text-muted italic py-2">
              Headlines unavailable at this time.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
