from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

RESPONDER_SYSTEM_PROMPT = """You are the response-writing node of a financial research agent.
Write a clear, concise answer using the tool results already in the conversation.
- Cite specific numbers from the tool results — never invent figures.
- If a tool returned an error, say so plainly instead of guessing.
- When citing information from annual reports or filings, mention the document title and section.
- For stock prices, surface the data's actual freshness using the 'as_of' timestamp (e.g., "as of 2:45 PM" or "as of yesterday's close") rather than claiming a price is "current" or real-time.
- Sound like a sharp research analyst, not a chatbot.
- Do not output JSON or markup of any kind — plain prose only. UI rendering is handled separately.
- When a MetricCard or PriceChart accompanies your answer, write 1–2 sentences of context or interpretation only. Do not restate every number the card already shows — only repeat a figure in prose if you're specifically commenting on it (e.g. "a P/E of 16 is low for an IT services peer group").
- Never mention charts, visuals, rendering, or interface limitations of any kind. Do not say what you "cannot" do. Just describe the financial data itself. Assume any relevant chart, card, or citation is already being shown to the user alongside your text.
"""

_llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.google_api_key, temperature=0.3)


async def responder_node(state):
    messages = [SystemMessage(content=RESPONDER_SYSTEM_PROMPT)] + list(state["messages"])
    response = await _llm.ainvoke(messages)
    ui_blocks = _build_ui_blocks(state.get("tool_trace", []))
    return {"messages": [response], "ui_blocks": ui_blocks}


def _build_ui_blocks(tool_trace: list[dict]) -> list[dict]:
    """Deterministic: turns verified tool output into UI blocks. The LLM never writes this JSON."""
    blocks = []
    for entry in tool_trace:
        if entry.get("error"):
            continue
        if entry["tool"] == "get_stock_price":
            props = dict(entry["raw_result"])
            ticker = props.get("ticker", "")
            props["currency"] = "INR" if ticker.endswith(".NS") or ticker.endswith(".BO") else "USD"
            blocks.append({"component": "PriceChart", "props": props})
        elif entry["tool"] == "get_financials":
            blocks.append({"component": "MetricCard", "props": _format_financials(entry["raw_result"])})
        elif entry["tool"] == "rag_search":
            raw = entry["raw_result"]
            results = raw.get("results", [])
            for result in results:
                blocks.append({
                    "component": "FilingExcerpt",
                    "props": {
                        "documentTitle": result.get("document_title", "Unknown"),
                        "sectionTitle": result.get("section_title", "General"),
                        "content": result.get("content", ""),
                        "ticker": result.get("ticker"),
                        "source": result.get("source", "seed"),
                        "relevanceScore": result.get("similarity"),
                    },
                })
    return blocks

def _format_financials(data: dict) -> dict:
    ticker = data.get("ticker", "")
    currency = "INR" if ticker.endswith((".NS", ".BO")) else "USD"

    dividend_yield = data.get("dividend_yield")
    if dividend_yield is not None and dividend_yield > 1:
        dividend_yield = dividend_yield / 100

    return {
        "ticker": ticker,
        "currency": currency,
        "metrics": [
            {"label": "P/E ratio", "value": data.get("pe_ratio"), "format": "number"},
            {"label": "EPS", "value": data.get("eps"), "format": "currency"},
            {"label": "Market cap", "value": data.get("market_cap"), "format": "compact"},
            {"label": "Dividend yield", "value": dividend_yield, "format": "percent"},
            {"label": "52w low", "value": data.get("fifty_two_week_low"), "format": "currency"},
            {"label": "52w high", "value": data.get("fifty_two_week_high"), "format": "currency"},
        ],
    }