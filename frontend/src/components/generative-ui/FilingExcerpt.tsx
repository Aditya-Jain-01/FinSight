"use client";

import { FilingExcerptProps } from "./schemas";

export function FilingExcerpt({
  documentTitle,
  sectionTitle,
  content,
  ticker,
  source,
  relevanceScore,
}: FilingExcerptProps) {
  return (
    <div className="bg-panel border border-border rounded-lg p-5 animate-slide-up my-4 shadow-sm relative">
      {/* Accent left bar */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent rounded-l-lg" />

      {/* Header */}
      <div className="flex items-start justify-between mb-4 pl-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            {ticker && (
              <span className="figure text-[10px] font-medium px-1.5 py-0.5 rounded bg-panel-muted border border-border text-text-primary uppercase">
                {ticker}
              </span>
            )}
            <span className="text-[10px] uppercase tracking-wider font-medium px-1.5 py-0.5 rounded bg-accent-muted text-accent">
              {source === "seed" ? "Annual Report" : "Uploaded"}
            </span>
            {relevanceScore !== undefined && (
              <span className="text-[10px] text-text-muted font-mono bg-page px-1.5 py-0.5 rounded">
                {(relevanceScore * 100).toFixed(0)}% match
              </span>
            )}
          </div>
          <h4 className="text-sm font-semibold text-text-primary leading-tight">
            {documentTitle}
          </h4>
          <p className="text-xs text-text-secondary mt-1">{sectionTitle}</p>
        </div>

        {/* Citation icon */}
        <div className="ml-4 text-accent bg-accent-muted p-1.5 rounded">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
      </div>

      {/* Excerpt content */}
      <div className="pl-2 ledger-rule mt-2">
        <blockquote className="text-sm text-text-primary leading-relaxed">
          <span className="footnote-mark mr-1">¹</span>
          {content}
        </blockquote>
      </div>
    </div>
  );
}
