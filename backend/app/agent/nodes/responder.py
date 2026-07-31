from collections.abc import AsyncIterator

from langchain_core.messages import SystemMessage
from app.config import settings
from app.agent.llm import get_llm

RESPONDER_SYSTEM_PROMPT = """You are the response-writing node of a financial research agent.
Write a clear, concise answer using the tool results already in the conversation.
- Cite specific numbers from the tool results — never invent figures.
- If a tool returned an error, say so plainly instead of guessing.
- When citing information from annual reports or filings, mention the document title and section.
- For stock prices, surface the data's actual freshness using the 'as_of' timestamp (e.g., "as of 2:45 PM" or "as of yesterday's close") rather than claiming a price is "current" or real-time.
- Sound like a sharp research analyst, not a chatbot.
- When comparing multiple companies or sections, explicitly use markdown subheadings (e.g., `### Naukri` or `### Financials`) rather than inline bold text.
- Do not output JSON or markup of any kind — plain prose and markdown formatting only. UI rendering is handled separately.
- A StockOverview card accompanies your answer for ticker queries. Write 1–2 sentences of context or interpretation only. Do not restate every number the card already shows — only repeat a figure in prose if you're specifically commenting on it (e.g. "a P/E of 16 is low for an IT services peer group").
- Never mention charts, visuals, rendering, or interface limitations of any kind. Do not say what you "cannot" do. Just describe the financial data itself. Assume any relevant chart, card, or citation is already being shown to the user alongside your text.
"""

_llm = get_llm()


def _extract_text(content) -> str:
    """Flatten content blocks (Gemini 3.5+ format) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


async def stream_responder_prose(messages: list) -> AsyncIterator[str]:
    """Stream prose tokens from the responder LLM.

    Called directly by chat_service.py for real token streaming,
    bypassing the LangGraph node system. All three providers in the
    fallback chain (Gemma, Nemotron, Llama) support .astream() via
    LangChain's standard interface.
    """
    full_messages = [SystemMessage(content=RESPONDER_SYSTEM_PROMPT)] + list(messages)
    async for chunk in _llm.astream(full_messages):
        text = _extract_text(chunk.content)
        if text:
            yield text


def build_ui_blocks_from_trace(tool_trace: list[dict]) -> list[dict]:
    """Deterministic UI block construction.

    Moved to a standalone function so chat_service.py can call it
    right after tool_executor completes, before streaming prose.
    """
    return _build_ui_blocks(tool_trace)

async def responder_node(state):
    # When chat_service streams prose directly via stream_responder_prose(),
    # it sets skip_responder=True to avoid a redundant LLM call here.
    if state.get("skip_responder"):
        return {"messages": [], "ui_blocks": [], "provider_meta": state.get("provider_meta", {})}

    messages = [SystemMessage(content=RESPONDER_SYSTEM_PROMPT)] + list(state["messages"])
    response = await _llm.ainvoke(messages)
    ui_blocks = _build_ui_blocks(state.get("tool_trace", []))

    print(f"\n  🧭 Responder received tool_results: {state.get('tool_trace')}")
    print(f"  🧭 Responder model content (raw): {repr(response.content)}")
    print(f"  🧭 Responder response_metadata: {response.response_metadata}")

    # Merge provider metadata from planner (if available) with responder info
    response_metadata = getattr(response, "response_metadata", {})
    provider_used = response_metadata.get("model_name", "unknown")
    provider_meta = state.get("provider_meta") or {"provider": provider_used, "model": provider_used}

    return {"messages": [response], "ui_blocks": ui_blocks, "provider_meta": provider_meta}


class UIBlockBuilder:
    """Aggregates tool results by ticker and emits one StockOverview block per ticker."""

    def __init__(self):
        self._ticker_data: dict[str, dict] = {}
        self._orphan_blocks: list[dict] = []  # null-ticker RAG results

    def _ensure_ticker(self, ticker: str) -> dict:
        if ticker not in self._ticker_data:
            self._ticker_data[ticker] = {
                "price": None,
                "metrics": [],
                "news": [],
                "excerpt": None,
                "sources": set(),
            }
        return self._ticker_data[ticker]

    def add_tool_result(self, entry: dict):
        tool = entry.get("tool", "")
        raw = entry.get("raw_result")

        # Skip internal/meta entries and errors
        if tool.startswith("_") or not raw or entry.get("error"):
            return
        if isinstance(raw, dict) and raw.get("error"):
            return

        if tool == "get_stock_price":
            ticker = raw.get("ticker", "")
            if not ticker:
                return
            data = self._ensure_ticker(ticker)
            history = raw.get("history", [])
            current = raw.get("current_price")
            first_close = history[0]["close"] if history else current
            change = round(current - first_close, 2) if current and first_close else 0
            change_pct = round(((current - first_close) / first_close) * 100, 2) if first_close else 0

            data["price"] = {
                "current": current,
                "change": change,
                "changePercent": change_pct,
                "asOf": raw.get("as_of", ""),
                "history": history,
            }
            data["sources"].add("yfinance")

        elif tool in ("get_financials", "get_company_info"):
            ticker = raw.get("ticker", "")
            if not ticker:
                return
            data = self._ensure_ticker(ticker)
            data["metrics"] = self._extract_metrics(raw)
            data["sources"].add("yfinance")

        elif tool == "get_stock_news":
            ticker = raw.get("ticker", "")
            if not ticker:
                return
            data = self._ensure_ticker(ticker)
            news_items = raw.get("news", [])
            data["news"] = [
                {
                    "title": n.get("title", ""),
                    "publisher": n.get("publisher"),
                    "link": n.get("link"),
                }
                for n in news_items[:3]
                if n.get("title")
            ]
            data["sources"].add("yfinance")

        elif tool == "rag_search":
            results = raw.get("results", [])
            for result in results:
                ticker = result.get("ticker")
                doc_title = result.get("document_title", "Unknown")
                content = result.get("content", "")

                if not ticker:
                    # Uploaded doc without a ticker → standalone FilingExcerpt
                    self._orphan_blocks.append({
                        "component": "FilingExcerpt",
                        "props": {
                            "documentTitle": doc_title,
                            "ticker": None,
                            "source": result.get("source", "uploaded"),
                            "excerpts": [{
                                "documentTitle": doc_title,
                                "sectionTitle": result.get("section_title", "General"),
                                "content": content,
                                "relevanceScore": result.get("similarity"),
                            }],
                        },
                    })
                    continue

                data = self._ensure_ticker(ticker)
                data["sources"].add(doc_title)
                # Take the first/highest-similarity excerpt for this ticker
                if data["excerpt"] is None:
                    data["excerpt"] = {
                        "documentTitle": doc_title,
                        "sectionTitle": result.get("section_title", "General"),
                        "content": content,
                        "source": result.get("source", "seed"),
                    }

    @staticmethod
    def _extract_metrics(raw: dict) -> list[dict]:
        """Extract metrics from get_financials/get_company_info results.

        Each metric is only included if its value is not None.
        NO ROCE, NO Promoter Holding — these are not yfinance fields.
        """
        candidates = [
            ("P/E Ratio", raw.get("pe_ratio"), "number"),
            ("EPS", raw.get("eps"), "currency"),
            ("Market Cap", raw.get("market_cap"), "compact"),
            ("Dividend Yield", _norm_pct(raw.get("dividend_yield")), "percent"),
            ("52w High", raw.get("fifty_two_week_high"), "currency"),
            ("52w Low", raw.get("fifty_two_week_low"), "currency"),
            ("Revenue", raw.get("total_revenue"), "compact"),
            ("Net Profit", raw.get("net_profit"), "compact"),
            ("Debt/Equity", _norm_de(raw.get("debt_to_equity")), "number"),
            ("ROE", _norm_pct(raw.get("roe")), "percent"),
        ]
        return [
            {"label": label, "value": value, "format": fmt}
            for label, value, fmt in candidates
            if value is not None
        ]

    def build(self) -> list[dict]:
        blocks: list[dict] = []
        for ticker, data in self._ticker_data.items():
            currency = "INR" if ticker.endswith((".NS", ".BO")) else "USD"
            props: dict = {
                "ticker": ticker,
                "currency": currency,
                "sources": sorted(data["sources"]),
            }

            if data["price"]:
                props["price"] = data["price"]
            if data["metrics"]:
                props["metrics"] = data["metrics"]
            if data["news"]:
                props["news"] = data["news"]
            if data["excerpt"]:
                props["filingExcerpt"] = data["excerpt"]

            blocks.append({"component": "StockOverview", "props": props})

        return blocks + self._orphan_blocks


def _norm_pct(val):
    """Normalize a percentage value: yfinance sometimes returns >1 for values like 0.45."""
    if val is None:
        return None
    if abs(val) > 1:
        return val / 100
    return val


def _norm_de(val):
    """Normalize debt-to-equity: yfinance often returns percentage form (e.g. 45.5 for 0.455)."""
    if val is None:
        return None
    if val > 5:
        return round(val / 100, 2)
    return round(val, 2)


def _build_ui_blocks(tool_trace: list[dict]) -> list[dict]:
    """Deterministic: turns verified tool output into deduplicated UI blocks. The LLM never writes this JSON."""
    builder = UIBlockBuilder()
    for entry in tool_trace:
        builder.add_tool_result(entry)
    return builder.build()