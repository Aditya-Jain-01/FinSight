"use client";

import { UIBlockSchema } from "./schemas";
import { getComponent } from "./registry";

interface BlockRendererProps {
  block: unknown;
}

/**
 * Validates an incoming ui_block against the Zod schema, then renders
 * the matched component. Never crashes on malformed data — shows a
 * quiet fallback instead.
 *
 * Design decision: the LLM never writes this JSON. The backend's
 * _build_ui_blocks function constructs it deterministically from tool
 * output. Zod validation here is a safety net, not a primary defense.
 */
export function BlockRenderer({ block }: BlockRendererProps) {
  const parsed = UIBlockSchema.safeParse(block);

  if (!parsed.success) {
    // Quiet fallback — log for debugging, don't crash the page
    console.warn("[BlockRenderer] Invalid ui_block:", parsed.error.format(), block);
    return (
      <div className="text-xs text-text-muted italic p-2 border border-border rounded mt-2">
        Unable to render this component
      </div>
    );
  }

  const { component, props } = parsed.data;
  const Component = getComponent(component);

  if (!Component) {
    console.warn(`[BlockRenderer] No component registered for "${component}"`);
    return null;
  }

  return (
    <div className="mt-3">
      <Component {...props} />
    </div>
  );
}
