import { z } from "zod";

/**
 * Zod schemas for each generative UI component.
 * These validate the JSON the backend emits deterministically from tool results.
 * The LLM never writes this JSON — _build_ui_blocks in responder.py does.
 */

// ─── Active schemas (emitted by current backend) ────────────────────

export const StockOverviewSchema = z.object({
  component: z.literal("StockOverview"),
  props: z.object({
    ticker: z.string(),
    companyName: z.string().optional(),
    currency: z.enum(["INR", "USD"]),
    price: z.object({
      current: z.number(),
      change: z.number(),
      changePercent: z.number(),
      asOf: z.string(),
      history: z.array(z.object({ date: z.string(), close: z.number() })),
    }).optional(),
    metrics: z.array(z.object({
      label: z.string(),
      value: z.number().nullable(),
      format: z.enum(["number", "currency", "percent", "compact"]),
    })).optional(),
    news: z.array(z.object({
      title: z.string(),
      publisher: z.string().optional(),
      link: z.string().optional(),
      timestamp: z.number().optional(),
    })).optional(),
    filingExcerpt: z.object({
      documentTitle: z.string(),
      sectionTitle: z.string(),
      content: z.string(),
      source: z.string(),
    }).optional(),
    sources: z.array(z.string()),
  }),
});

export const AgentTraceSchema = z.object({
  component: z.literal("AgentTrace"),
  props: z.object({
    toolCalls: z.array(
      z.object({
        tool: z.string(),
        args: z.record(z.unknown()),
        latency_ms: z.number(),
        raw_result: z.unknown(),
        error: z.string().nullable().optional(),
      })
    ),
    totalLatencyMs: z.number(),
  }),
});

// ─── Legacy schemas (kept for backward compat with old persisted messages) ──

export const PriceChartSchema = z.object({
  component: z.literal("PriceChart"),
  props: z.object({
    ticker: z.string(),
    currency: z.enum(["INR", "USD"]).optional(),
    current_price: z.number(),
    as_of: z.string().optional(),
    period: z.string(),
    history: z.array(
      z.object({
        date: z.string(),
        close: z.number(),
      })
    ),
  }),
});

export const MetricCardSchema = z.object({
  component: z.literal('MetricCard'),
  props: z.object({
    ticker: z.string(),
    currency: z.enum(['INR', 'USD']),
    metrics: z.array(z.object({
      label: z.string(),
      value: z.number().nullable(),
      format: z.enum(['number', 'currency', 'percent', 'compact']).default('number'),
    })),
  }),
});

export const FilingExcerptSchema = z.object({
  component: z.literal("FilingExcerpt"),
  props: z.object({
    documentTitle: z.string(),
    ticker: z.string().nullish(),
    source: z.string(),
    excerpts: z.array(
      z.object({
        sectionTitle: z.string(),
        content: z.string(),
        relevanceScore: z.number().optional(),
      })
    ),
  }),
});

export const MarketBriefSchema = z.object({
  component: z.literal("MarketBrief"),
  props: z.record(z.unknown()).optional(),
});

export const ResearchCardSchema = z.object({
  component: z.literal("ResearchCard"),
  props: z.object({
    ticker: z.string(),
    currency: z.enum(["INR", "USD"]).optional(),
    currentPrice: z.number().optional(),
    lastUpdated: z.string().optional(),
    period: z.string().optional(),
    historicalPrices: z.array(z.object({
      date: z.string(),
      close: z.number(),
    })).optional(),
    keyMetrics: z.array(z.object({
      label: z.string(),
      value: z.number().nullable(),
      format: z.string(),
    })).optional(),
    kpis: z.array(z.object({
      label: z.string(),
      value: z.number().nullable(),
      format: z.string(),
    })).optional(),
    news: z.array(z.object({
      title: z.string(),
      publisher: z.string().optional(),
      link: z.string().optional(),
      timestamp: z.number().optional(),
    })).optional(),
    excerpts: z.array(z.object({
      documentTitle: z.string(),
      sectionTitle: z.string(),
      content: z.string(),
      relevanceScore: z.number().optional(),
    })).optional(),
    sources: z.array(z.string()).optional(),
  }),
});

// ─── Union (all component types the frontend can render) ────────────

export const UIBlockSchema = z.discriminatedUnion("component", [
  StockOverviewSchema,
  AgentTraceSchema,
  PriceChartSchema,
  MetricCardSchema,
  FilingExcerptSchema,
  MarketBriefSchema,
  ResearchCardSchema,
]);

// ─── Type exports ───────────────────────────────────────────────────

export type StockOverviewProps = z.infer<typeof StockOverviewSchema>["props"];
export type AgentTraceProps = z.infer<typeof AgentTraceSchema>["props"];
export type PriceChartProps = z.infer<typeof PriceChartSchema>["props"];
export type MetricCardProps = z.infer<typeof MetricCardSchema>["props"];
export type FilingExcerptProps = z.infer<typeof FilingExcerptSchema>["props"];
export type MarketBriefProps = z.infer<typeof MarketBriefSchema>["props"];
export type ResearchCardProps = z.infer<typeof ResearchCardSchema>["props"];
export type UIBlock = z.infer<typeof UIBlockSchema>;

export type NewsListProps = {
  ticker?: string;
  news?: {
    title: string;
    publisher?: string;
    link?: string;
    timestamp?: number;
  }[];
};
