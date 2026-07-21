import { ComponentType } from "react";
import { PriceChart } from "./PriceChart";
import { AgentTrace } from "./AgentTrace";
import { FilingExcerpt } from "./FilingExcerpt";
import { MetricCard } from "./MetricCard";
import type { PriceChartProps, AgentTraceProps, FilingExcerptProps, MetricCardProps } from "./schemas";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyProps = any;

const REGISTRY: Record<string, ComponentType<AnyProps>> = {
  PriceChart: PriceChart as ComponentType<AnyProps>,
  AgentTrace: AgentTrace as ComponentType<AnyProps>,
  FilingExcerpt: FilingExcerpt as ComponentType<AnyProps>,
  MetricCard: MetricCard as ComponentType<AnyProps>,
};

export function getComponent(name: string): ComponentType<AnyProps> | undefined {
  return REGISTRY[name];
}

export type { PriceChartProps, AgentTraceProps, FilingExcerptProps, MetricCardProps };
