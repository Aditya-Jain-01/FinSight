import time
from fastapi import APIRouter
from app.services.market_brief_service import get_market_brief

router = APIRouter()

_cache = {}
CACHE_TTL = 300 # 5 minutes

@router.get("/brief")
async def market_brief_route():
    cache_key = "market_brief"
    now = time.time()
    
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    brief = await get_market_brief()
    _cache[cache_key] = (now, brief)
    return brief
