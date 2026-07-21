import { z } from "zod";

/**
 * Zod schemas for each generative UI component.
 * These validate the JSON the backend emits deterministically from tool results.
 * The LLM never writes this JSON — _build_ui_blocks in responder.py does.
 */

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

export const FilingExcerptSchema = z.object({
  component: z.literal("FilingExcerpt"),
  props: z.object({
    documentTitle: z.string(),
    sectionTitle: z.string(),
    content: z.string(),
    ticker: z.string().optional(),
    source: z.string(),
    relevanceScore: z.number().optional(),
  }),
});

export const UIBlockSchema = z.discriminatedUnion("component", [
  PriceChartSchema,
  MetricCardSchema,
  AgentTraceSchema,
  FilingExcerptSchema,
]);

export type PriceChartProps = z.infer<typeof PriceChartSchema>["props"];
export type MetricCardProps = z.infer<typeof MetricCardSchema>["props"];
export type AgentTraceProps = z.infer<typeof AgentTraceSchema>["props"];
export type FilingExcerptProps = z.infer<typeof FilingExcerptSchema>["props"];
export type UIBlock = z.infer<typeof UIBlockSchema>;
