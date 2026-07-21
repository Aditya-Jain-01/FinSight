from langchain_core.tools import tool
import yfinance as yf


@tool
def get_stock_price(ticker: str, period: str = "1mo") -> dict:
    """Get the current price and historical closing prices for an Indian or US stock."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    if hist.empty:
        return {"error": f"No price data found for '{ticker}'. Check the ticker symbol and exchange suffix."}

    history = [
        {"date": str(idx.date()), "close": round(float(row["Close"]), 2)}
        for idx, row in hist.iterrows()
    ]

    # The daily series above only updates once per day at close — it doesn't reflect
    # intraday moves. Pull the most recent 1-minute bar separately for the actual
    # current/near-real-time price.
    current_price = history[-1]["close"]
    as_of = history[-1]["date"]
    try:
        intraday = stock.history(period="1d", interval="1m")
        if not intraday.empty:
            current_price = round(float(intraday["Close"].iloc[-1]), 2)
            as_of = str(intraday.index[-1])
    except Exception:
        pass  # falls back to the daily close above — still correct, just not intraday

    return {
        "ticker": ticker,
        "current_price": current_price,
        "as_of": as_of,
        "period": period,
        "history": history,
    }