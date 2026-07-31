import asyncio
import time
from fastapi import APIRouter, Query, HTTPException
import yfinance as yf

router = APIRouter()

_cache = {}
CACHE_TTL = 300

async def fetch_ticker_data(ticker: str):
    cache_key = ticker.upper()
    now = time.time()
    
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return ticker, cached_data, None

    try:
        # yfinance operations are blocking, run in executor
        loop = asyncio.get_running_loop()
        stock = await loop.run_in_executor(None, yf.Ticker, ticker)
        info = await loop.run_in_executor(None, lambda: stock.info)
        
        result = {
            "ticker": ticker.upper(),
            "shortName": info.get("shortName", ticker.upper()),
            "currentPrice": info.get("currentPrice"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "revenueGrowth": info.get("revenueGrowth"),
            "returnOnEquity": info.get("returnOnEquity"),
            "debtToEquity": info.get("debtToEquity"),
            "dividendYield": info.get("dividendYield"),
            "profitMargins": info.get("profitMargins")
        }
        
        _cache[cache_key] = (now, result)
        return ticker, result, None
    except Exception as e:
        return ticker, None, str(e)

@router.get("/")
async def compare_tickers(tickers: str = Query(..., description="Comma-separated tickers")):
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")
    
    if len(ticker_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 tickers allowed for comparison")

    tasks = [fetch_ticker_data(t) for t in ticker_list]
    results = await asyncio.gather(*tasks)
    
    success = []
    failed = []
    
    for ticker, data, err in results:
        if err or not data:
            failed.append({"ticker": ticker, "error": err or "Failed to fetch data"})
        else:
            success.append(data)
            
    return {
        "results": success,
        "failed": failed
    }
