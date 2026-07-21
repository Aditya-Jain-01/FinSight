from langchain_core.tools import tool
import yfinance as yf


@tool
def get_stock_news(ticker: str, limit: int = 5) -> dict:
    """Get recent news headlines for an Indian stock.
    ticker must include exchange suffix, e.g. 'HDFCBANK.NS'.
    """
    stock = yf.Ticker(ticker)
    news = stock.news or []

    # yfinance's news payload shape has shifted between versions — print(news[0])
    # once locally and adjust these keys if they don't match what you see.
    items = [
        {
            "title": (n.get("content") or {}).get("title") or n.get("title"),
            "publisher": ((n.get("content") or {}).get("provider") or {}).get("displayName") or n.get("publisher"),
            "link": ((n.get("content") or {}).get("canonicalUrl") or {}).get("url") or n.get("link"),
        }
        for n in news[:limit]
    ]
    items = [i for i in items if i["title"]]
    if not items:
        return {"error": f"No news found for '{ticker}'."}
    return {"ticker": ticker, "news": items}