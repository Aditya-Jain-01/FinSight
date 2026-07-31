import time
from fastapi import APIRouter, HTTPException
import yfinance as yf

router = APIRouter()

# Simple in-memory cache: { "TICKER": (timestamp, data) }
# Cache for 5 minutes (300s)
_cache = {}
CACHE_TTL = 300 

@router.get("/financials/{ticker}")
async def get_financials_route(ticker: str):
    cache_key = ticker.upper()
    now = time.time()
    
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # We need trailingPE and trailingEps for the valuation sandbox
        # Some tickers might be missing these fields, provide None if so
        result = {
            "ticker": ticker.upper(),
            "trailingPE": info.get("trailingPE"),
            "trailingEps": info.get("trailingEps"),
        }
        
        _cache[cache_key] = (now, result)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
