import asyncio
import yfinance as yf
import requests

# Common indices for US and India
INDICES = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN"
}

# A small universe of popular stocks to simulate "movers" without a full screener API
UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS"
]

async def fetch_ticker_summary(ticker_symbol: str):
    loop = asyncio.get_running_loop()
    try:
        t = await loop.run_in_executor(None, yf.Ticker, ticker_symbol)
        info = await loop.run_in_executor(None, lambda: t.info)
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        
        if current_price and previous_close and previous_close > 0:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
        else:
            change = 0
            change_percent = 0
            
        return {
            "symbol": ticker_symbol,
            "name": info.get("shortName", ticker_symbol),
            "price": current_price,
            "change": change,
            "change_percent": change_percent
        }
    except Exception:
        return None

async def fetch_market_news(query="market", market_tag="US"):
    loop = asyncio.get_running_loop()
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = f'https://query2.finance.yahoo.com/v1/finance/search?q={query}&newsCount=5'
        
        def _fetch():
            res = requests.get(url, headers=headers, timeout=10.0)
            res.raise_for_status()
            return res.json()
            
        data = await loop.run_in_executor(None, _fetch)
        raw_news = data.get("quotes", []) + data.get("news", [])
            
        news = []
        for n in raw_news:
            if "title" in n and "link" in n:
                news.append({
                    "title": n.get("title", ""),
                    "publisher": n.get("publisher", ""),
                    "link": n.get("link", ""),
                    "time": n.get("providerPublishTime", 0),
                    "market": market_tag
                })
        return news[:5]
    except Exception:
        return []

async def get_market_brief():
    # Fetch indices
    indices_tasks = [fetch_ticker_summary(sym) for sym in INDICES.values()]
    
    # Fetch universe for movers
    universe_tasks = [fetch_ticker_summary(sym) for sym in UNIVERSE]
    
    results = await asyncio.gather(*(indices_tasks + universe_tasks))
    
    indices_results = results[:len(INDICES)]
    universe_results = results[len(INDICES):]
    
    # Filter valid results
    valid_indices = []
    for name, sym in INDICES.items():
        res = next((r for r in indices_results if r and r["symbol"] == sym), None)
        if res:
            res["name"] = name  
            valid_indices.append(res)
            
    valid_universe = [r for r in universe_results if r is not None]
    
    us_universe = [r for r in valid_universe if not r["symbol"].endswith(".NS")]
    in_universe = [r for r in valid_universe if r["symbol"].endswith(".NS")]
    
    us_universe.sort(key=lambda x: x["change_percent"], reverse=True)
    in_universe.sort(key=lambda x: x["change_percent"], reverse=True)
    
    us_gainers = [x for x in us_universe if x["change_percent"] > 0][:3]
    us_losers = [x for x in us_universe[::-1] if x["change_percent"] < 0][:3]
    
    in_gainers = [x for x in in_universe if x["change_percent"] > 0][:3]
    in_losers = [x for x in in_universe[::-1] if x["change_percent"] < 0][:3]
    
    us_news, in_news = await asyncio.gather(
        fetch_market_news("US stock market", market_tag="US"),
        fetch_market_news("India stock market", market_tag="IN")
    )

    return {
        "indices": valid_indices,
        "us": {
            "gainers": us_gainers,
            "losers": us_losers,
            "news": us_news
        },
        "in": {
            "gainers": in_gainers,
            "losers": in_losers,
            "news": in_news
        }
    }
