from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.agent.tools.registry import TOOLS

PLANNER_SYSTEM_PROMPT = """You are the planning node of a financial research agent covering both
Indian and US markets.

- Indian tickers use exchange suffixes: .NS for NSE, .BO for BSE (e.g. RELIANCE.NS, TCS.NS, INFY.BO, HDFCBANK.NS).
- US tickers use NO suffix (e.g. AAPL, MSFT, GOOGL, TSLA).
- If the user names an Indian company without a suffix, infer the correct ticker and default to .NS.
- If the user names a US company without a suffix, use the plain ticker with no suffix.
- If ambiguous which market a company belongs to, prefer the market implied by context, or ask by
  proceeding with the most likely interpretation rather than blocking.
- Call whichever tools are needed to answer accurately — call multiple tools if the question needs them.
- If the question doesn't need live data (a greeting, a definition, small talk), don't call any tools.
- For questions about annual reports, filings, capex plans, management commentary, revenue breakdowns,
  risk factors, or strategic initiatives — use the rag_search tool. Pass the ticker if you know it.
- You can combine rag_search with other tools. For example, if asked "What is Reliance's capex plan
  and current stock price?", call both rag_search and get_stock_price.
"""

_llm = ChatGroq(
    model=settings.groq_model,
    api_key=settings.groq_api_key,
    temperature=0,
)
_llm_with_tools = _llm.bind_tools(TOOLS)


async def planner_node(state):
    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=PLANNER_SYSTEM_PROMPT)] + messages

    response = await _llm_with_tools.ainvoke(messages)

    # Extract which provider actually handled this request
    provider_meta = {"provider": "Groq", "model": settings.groq_model}

    return {
        "messages": [response],
        "provider_meta": provider_meta,
    }