import time
from fastapi import APIRouter, HTTPException
import yfinance as yf

router = APIRouter()

# Simple in-memory cache: { "TICKER_PERIOD": (timestamp, data) }
# Cache for 60 seconds to prevent rate limits on rapid tab clicking
_cache = {}
CACHE_TTL = 60 

@router.get("/chart/{ticker}")
async def get_chart(ticker: str, period: str = "1mo"):
    cache_key = f"{ticker}_{period}"
    now = time.time()
    
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    try:
        stock = yf.Ticker(ticker)
        # For "Max" we usually pass "max" to yfinance
        hist = stock.history(period=period)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="No price data found")

        history = [
            {"date": str(idx.date()), "close": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
        
        result = {
            "ticker": ticker,
            "period": period,
            "history": history
        }
        
        _cache[cache_key] = (now, result)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
