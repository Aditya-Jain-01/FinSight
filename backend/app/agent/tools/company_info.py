from langchain_core.tools import tool
import yfinance as yf


@tool
def get_company_info(ticker: str) -> dict:
    """Get company profile info for an Indian stock: sector, industry, business
    summary, website. ticker must include exchange suffix, e.g. 'INFY.NS'.
    """
    info = yf.Ticker(ticker).info
    if not info or info.get("longName") is None:
        return {"error": f"No company info found for '{ticker}'."}

    return {
        "ticker": ticker,
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "summary": info.get("longBusinessSummary"),
        "website": info.get("website"),
    }