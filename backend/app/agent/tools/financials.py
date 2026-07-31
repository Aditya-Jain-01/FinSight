from langchain_core.tools import tool
import yfinance as yf


@tool
def get_financials(ticker: str) -> dict:
    """Get key financial ratios for a stock: P/E ratio, market cap, EPS,
    dividend yield, 52-week high/low, revenue, net profit, debt/equity, ROE.
    ticker must include exchange suffix for Indian stocks, e.g. 'TCS.NS'.
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
        "total_revenue": info.get("totalRevenue"),
        "net_profit": info.get("netIncomeToCommon"),
        "debt_to_equity": info.get("debtToEquity"),
        "roe": info.get("returnOnEquity"),
    }