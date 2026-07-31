from fastapi import APIRouter

from app.api.v1 import chat, documents, health, ws_documents, ws_prices, chart, compare, market

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(ws_documents.router, tags=["websocket"])
api_router.include_router(ws_prices.router, tags=["websocket"])
api_router.include_router(chart.router, tags=["chart"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(market.router, prefix="/market", tags=["market"])