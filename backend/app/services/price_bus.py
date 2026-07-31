"""Live price streaming: Finnhub WebSocket (US) + yfinance poll (India).

Singleton Finnhub connection shared across all client WebSocket connections.
India tickers get polled via yfinance at ~10s intervals (capped at 15 concurrent).

Architecture:
- _subscribers: ticker → set of asyncio.Queue (one per client WS connection)
- _finnhub_ws: single persistent WebSocket to Finnhub
- _poll_tasks: ticker → asyncio.Task for India yfinance poll loops
"""

import asyncio
import json
import logging
import time

import yfinance as yf
from websockets.client import connect as ws_connect

from app.config import settings

logger = logging.getLogger(__name__)

# --- Subscriber registry ---
# ticker → set of asyncio.Queue
_subscribers: dict[str, set[asyncio.Queue]] = {}

# --- Finnhub singleton ---
_finnhub_ws = None  # The persistent WebSocket connection
_finnhub_task: asyncio.Task | None = None  # Task running the Finnhub listener

# --- India poll tasks ---
# ticker → asyncio.Task running the yfinance poll loop
_poll_tasks: dict[str, asyncio.Task] = {}

MAX_INDIA_POLLS = 15  # Cap concurrent poll loops


def _is_india_ticker(ticker: str) -> bool:
    return ticker.upper().endswith((".NS", ".BO"))


async def _publish_price(ticker: str, price: float, timestamp: float | None = None):
    """Fan out a price update to all subscribers for a ticker."""
    event = {"ticker": ticker, "price": price, "timestamp": timestamp or time.time()}
    for queue in _subscribers.get(ticker, set()).copy():
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


# --- Finnhub WebSocket ---

async def _finnhub_listener():
    """Persistent Finnhub WS connection. Reconnects on drop."""
    global _finnhub_ws
    while True:
        try:
            async with ws_connect(f"wss://ws.finnhub.io?token={settings.finnhub_api_key}") as ws:
                _finnhub_ws = ws
                logger.info("Finnhub WS connected")

                # Re-subscribe all current US tickers
                for ticker in list(_subscribers.keys()):
                    if not _is_india_ticker(ticker):
                        await ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))

                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("type") == "trade":
                        for trade in data.get("data", []):
                            symbol = trade.get("s")
                            price = trade.get("p")
                            ts = trade.get("t", 0) / 1000  # ms → s
                            if symbol and price:
                                await _publish_price(symbol, price, ts)

        except Exception as e:
            logger.warning("Finnhub WS dropped (%s), reconnecting in 5s...", e)
            _finnhub_ws = None
            await asyncio.sleep(5)


async def start_finnhub(app):
    """Called from main.py lifespan to start the singleton Finnhub listener."""
    global _finnhub_task
    if settings.finnhub_api_key:
        _finnhub_task = asyncio.create_task(_finnhub_listener())
        logger.info("Finnhub listener task started")
    else:
        logger.info("Finnhub API key not set — live US price streaming disabled")


async def stop_finnhub():
    """Called from main.py lifespan teardown."""
    global _finnhub_task
    if _finnhub_task:
        _finnhub_task.cancel()
        try:
            await _finnhub_task
        except asyncio.CancelledError:
            pass


# --- India yfinance poll ---

async def _india_poll_loop(ticker: str, interval: float = 10.0):
    """Poll yfinance for India ticker prices at a fixed interval."""
    while True:
        try:
            # Run in executor since yfinance is sync
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: yf.Ticker(ticker).fast_info)
            price = getattr(info, "last_price", None)
            if price:
                await _publish_price(ticker, float(price))
        except Exception as e:
            logger.debug("India poll error for %s: %s", ticker, e)
        await asyncio.sleep(interval)


# --- Public API ---

def subscribe(ticker: str) -> asyncio.Queue:
    """Subscribe to price updates for a ticker."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    is_first = ticker not in _subscribers or len(_subscribers[ticker]) == 0
    _subscribers.setdefault(ticker, set()).add(queue)

    if is_first:
        if _is_india_ticker(ticker):
            if len(_poll_tasks) < MAX_INDIA_POLLS:
                task = asyncio.create_task(_india_poll_loop(ticker))
                _poll_tasks[ticker] = task
        else:
            # Send Finnhub subscribe message
            if _finnhub_ws:
                asyncio.create_task(
                    _finnhub_ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
                )

    return queue


def unsubscribe(ticker: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from price updates. Cleans up when last subscriber leaves."""
    subs = _subscribers.get(ticker)
    if subs:
        subs.discard(queue)
        if not subs:
            del _subscribers[ticker]
            # Last subscriber — clean up
            if _is_india_ticker(ticker):
                task = _poll_tasks.pop(ticker, None)
                if task:
                    task.cancel()
            else:
                if _finnhub_ws:
                    asyncio.create_task(
                        _finnhub_ws.send(json.dumps({"type": "unsubscribe", "symbol": ticker}))
                    )
