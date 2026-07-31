"""WebSocket endpoint for real-time price streaming (Phase 3)."""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.price_bus import subscribe, unsubscribe

router = APIRouter()

@router.websocket("/ws/prices/{ticker}")
async def price_stream_ws(websocket: WebSocket, ticker: str):
    await websocket.accept()
    queue = subscribe(ticker)
    try:
        while True:
            # Wait for price updates from the bus
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass  # Client disconnected normally
    finally:
        unsubscribe(ticker, queue)
