"use client";

type Metric = { label: string; value: number | null; format: 'number' | 'currency' | 'percent' | 'compact' };

function formatMetric(value: number | null, format: Metric['format'], currency: string): string {
  if (value === null) return '—';
  const symbol = currency === 'INR' ? '₹' : '$';
  switch (format) {
    case 'currency': return `${symbol}${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    case 'percent': return `${(value * 100).toFixed(2)}%`;
    case 'compact': return `${symbol}${new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 2 }).format(value)}`;
    default: return value.toFixed(2);
  }
}

export function MetricCard({ ticker, currency, metrics }: { ticker: string; currency: string; metrics: Metric[] }) {
  return (
    <div className="animate-slide-up my-4">
      {ticker && (
        <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-2">
          {ticker} Financials
        </h4>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
      {metrics.map((m) => (
        <div key={m.label} style={{ background: 'var(--bg-panel-muted)', borderRadius: 8, padding: '8px 10px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{m.label}</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-primary)', marginTop: 2 }}>
            {formatMetric(m.value, m.format, currency)}
          </div>
        </div>
      ))}
      </div>
    </div>
  );
}
