from langchain_core.messages import SystemMessage
from app.config import settings
from app.agent.tools.registry import TOOLS
from app.agent.llm import get_llm_with_tools

PLANNER_SYSTEM_PROMPT = """You are the planning node of a financial research agent covering both
Indian and US markets.

- Indian tickers use exchange suffixes: .NS for NSE, .BO for BSE (e.g. RELIANCE.NS, TCS.NS, INFY.BO, HDFCBANK.NS).
- US tickers use NO suffix (e.g. AAPL, MSFT, GOOGL, TSLA).
- If the user names an Indian company without a suffix, infer the correct ticker and default to .NS.
- If the user names a US company without a suffix, use the plain ticker with no suffix.
- If ambiguous which market a company belongs to, prefer the market implied by context, or ask by
  proceeding with the most likely interpretation rather than blocking.

TOOL BUNDLING (important):
- When the user asks about a SPECIFIC company or ticker — whether it's about price, financials,
  overview, analysis, news, or any question where a ticker is the subject — call ALL THREE of
  these tools together in one turn:
    1. get_stock_price
    2. get_financials
    3. get_stock_news
  This produces a unified overview card. Do NOT pick just one tool — always call the full bundle
  for any ticker-specific query.
- For non-ticker questions (definitions, greetings, general finance concepts, comparisons that
  don't need new data), keep current behavior — call only what's needed or nothing at all.
- If the user asks about their portfolio, holdings, or P&L, call the `get_portfolio_holdings` tool.

- CRITICAL: Do NOT call the same tool twice with the same arguments in a single turn.
- CRITICAL: Do NOT call a tool for information you already fetched in a previous turn unless the user explicitly asks for an update.
- If the question doesn't need live data (a greeting, a definition, small talk), don't call any tools."""

_rag_instructions = """
- For questions about annual reports, filings, capex plans, management commentary, revenue breakdowns,
  risk factors, or strategic initiatives — use the rag_search tool. Pass the ticker if you know it.
- If the user references an uploaded document ('the pdf', 'this report', 'the document') without naming
  a company, call rag_search with just the query — do not ask for a ticker first in this case.
- You can combine rag_search with other tools. For example, if asked "What is Reliance's capex plan
  and current stock price?", call both rag_search and get_stock_price.
"""

_llm_with_tools = get_llm_with_tools(TOOLS)

async def planner_node(state):
    messages = list(state["messages"])
    has_user_docs = state.get("has_user_docs", False)
    
    if not messages or not isinstance(messages[0], SystemMessage):
        prompt = PLANNER_SYSTEM_PROMPT
        if has_user_docs:
            prompt += _rag_instructions
        messages = [SystemMessage(content=prompt)] + messages

    # Gate rag_search behind user-uploaded documents
    available_tools = []
    for tool in TOOLS:
        if tool.name == "rag_search":
            if state.get("has_user_docs", False):
                available_tools.append(tool)
        else:
            available_tools.append(tool)
    print(f"\n  🧭 has_user_docs flag: {state.get('has_user_docs')}")
    print(f"  🧭 Planner tools available: {[t.name for t in available_tools]}")
            
    _llm_with_tools_dynamic = get_llm_with_tools(available_tools)

    response = await _llm_with_tools_dynamic.ainvoke(messages)

    print(f"  🧭 Model returned tool_calls: {response.tool_calls}")
    print(f"  🧭 Model content (if any): {repr(response.content)}")
    print(f"  🧭 response_metadata: {response.response_metadata}")

    # Extract which provider actually handled this request
    response_metadata = getattr(response, "response_metadata", {})
    provider_used = response_metadata.get("model_name", "unknown")
    provider_meta = {"provider": provider_used, "model": provider_used}

    return {
        "messages": [response],
        "provider_meta": provider_meta,
    }