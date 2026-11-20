"""
FastAPI Dependencies for RULLY Mini App API.
"""

import os
import time
from fastapi import Header, Query, HTTPException, Depends
from typing import Optional, Dict, Any, Tuple
from src.api.security import verify_telegram_init_data
from src.bot.database import BotDatabase

def get_db() -> BotDatabase:
    return BotDatabase("master_database.sqlite")

# Fast in-memory user cache (30s TTL) to eliminate repetitive Turso roundtrips
_user_cache: Dict[int, Tuple[float, Dict[str, Any]]] = {}
USER_CACHE_TTL = 30.0

def invalidate_user_cache(user_id: int):
    """Evicts a user from cache when subscription or profile changes."""
    _user_cache.pop(user_id, None)

async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    init_data: Optional[str] = Query(None, alias="initData"),
    db: BotDatabase = Depends(get_db)
) -> Dict[str, Any]:
    raw_data = x_telegram_init_data or init_data

    # Development fallback
    if not raw_data or str(raw_data).strip().lower() in ["null", "undefined", "none", ""]:
        is_prod = os.getenv("ENVIRONMENT", "").lower() == "production" or bool(os.getenv("VERCEL"))
        if is_prod:
            raise HTTPException(status_code=401, detail="Missing Telegram authentication data")

        # Default dev user for local testing and direct browser previews only
        dev_id = 8809526955
        now = time.time()
        if dev_id in _user_cache and (now - _user_cache[dev_id][0]) < USER_CACHE_TTL:
            return _user_cache[dev_id][1]

        user = db.get_or_create_user(
            user_id=dev_id,
            username="kurs_savdo",
            first_name="RULLY User",
            last_name=""
        )
        _user_cache[dev_id] = (now, user)
        return user

    is_valid, user_data = verify_telegram_init_data(raw_data)
    if not is_valid or not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID in authentication data")

    now = time.time()
    if user_id in _user_cache and (now - _user_cache[user_id][0]) < USER_CACHE_TTL:
        return _user_cache[user_id][1]

    user = db.get_or_create_user(
        user_id=user_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name", "Haydovchi"),
        last_name=user_data.get("last_name", "")
    )
    _user_cache[user_id] = (now, user)
    return user
