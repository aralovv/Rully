"""
FastAPI Dependencies for RULLY Mini App API.
"""

import os
import time
from fastapi import Header, Query, HTTPException, Depends
from typing import Optional, Dict, Any, Tuple
from src.api.security import verify_telegram_init_data, is_production
from src.bot.database import BotDatabase
from src.security.rate_limiter import BoundedTTLCache

import os

def get_db() -> BotDatabase:
    return BotDatabase(os.getenv("DB_PATH", "master_database.sqlite"))

# Fast bounded in-memory user cache (30s TTL, max 2000 items) to eliminate repetitive Turso roundtrips
_user_cache = BoundedTTLCache[int, Dict[str, Any]](maxsize=2000, ttl_seconds=30.0)

def invalidate_user_cache(user_id: int):
    """Evicts a user from both deps user cache and auth bundle cache when subscription or block status changes."""
    _user_cache.pop(user_id, None)
    try:
        from src.api.routes_auth import _AUTH_BUNDLE_CACHE
        _AUTH_BUNDLE_CACHE.pop(user_id, None)
    except Exception:
        pass

def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    db: BotDatabase = Depends(get_db)
) -> Dict[str, Any]:
    raw_data = x_telegram_init_data

    # Development fallback
    if not raw_data or str(raw_data).strip().lower() in ["null", "undefined", "none", ""]:
        if is_production():
            raise HTTPException(status_code=401, detail="Missing Telegram authentication data")

        # Default dev user for local testing and direct browser previews only
        dev_id = 8809526955
        cached = _user_cache.get(dev_id)
        if cached:
            return cached

        user = db.get_or_create_user(
            user_id=dev_id,
            username="kurs_savdo",
            first_name="RULLY User",
            last_name=""
        )
        _user_cache.set(dev_id, user)
        return user

    is_valid, user_data = verify_telegram_init_data(raw_data)
    if not is_valid or not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID in authentication data")

    cached = _user_cache.get(user_id)
    if cached:
        if int(cached.get("is_blocked") or 0) == 1:
            raise HTTPException(status_code=403, detail="USER_BLOCKED: Sizning hisobingiz bloklangan.")
        return cached

    user = db.get_or_create_user(
        user_id=user_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name", "Haydovchi"),
        last_name=user_data.get("last_name", "")
    )
    _user_cache.set(user_id, user)
    if int(user.get("is_blocked") or 0) == 1:
        raise HTTPException(status_code=403, detail="USER_BLOCKED: Sizning hisobingiz bloklangan.")
    return user
