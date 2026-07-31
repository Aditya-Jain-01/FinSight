import { ComponentType } from "react";
import { StockOverview } from "./StockOverview";
import { PriceChart } from "./PriceChart";
import { AgentTrace } from "./AgentTrace";
import { FilingExcerpt } from "./FilingExcerpt";
import { MetricCard } from "./MetricCard";
import { MarketBrief } from "./MarketBrief";
import type {
  StockOverviewProps,
  AgentTraceProps,
  PriceChartProps,
  MetricCardProps,
  FilingExcerptProps,
  MarketBriefProps,
} from "./schemas";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyProps = any;

const REGISTRY: Record<string, ComponentType<AnyProps>> = {
  // Active — emitted by current backend
  StockOverview: StockOverview as ComponentType<AnyProps>,
  AgentTrace: AgentTrace as ComponentType<AnyProps>,
  MarketBrief: MarketBrief as ComponentType<AnyProps>,
  // Legacy — kept for old persisted messages
  PriceChart: PriceChart as ComponentType<AnyProps>,
  FilingExcerpt: FilingExcerpt as ComponentType<AnyProps>,
  MetricCard: MetricCard as ComponentType<AnyProps>,
};

export function getComponent(name: string): ComponentType<AnyProps> | undefined {
  return REGISTRY[name];
}

export type { StockOverviewProps, AgentTraceProps, PriceChartProps, MetricCardProps, FilingExcerptProps };
