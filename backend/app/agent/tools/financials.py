from langchain_core.tools import tool
import yfinance as yf


@tool
def get_financials(ticker: str) -> dict:
    """Get key financial ratios for an Indian stock: P/E ratio, market cap, EPS,
    dividend yield, 52-week high/low. ticker must include exchange suffix, e.g. 'TCS.NS'.
    """
    info = yf.Ticker(ticker).info
    if not info or info.get("regularMarketPrice") is None:
        return {"error": f"No financial data found for '{ticker}'."}

    return {
        "ticker": ticker,
        "pe_ratio": info.get("trailingPE"),
        "market_cap": info.get("marketCap"),
        "eps": info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
    }