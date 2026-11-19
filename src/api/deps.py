"""
FastAPI Dependencies for RULLY Mini App API.
"""

import os
from fastapi import Header, Query, HTTPException, Depends
from typing import Optional, Dict, Any
from src.api.security import verify_telegram_init_data
from src.bot.database import BotDatabase

def get_db() -> BotDatabase:
    return BotDatabase("master_database.sqlite")

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
        user = db.get_or_create_user(
            user_id=8809526955,
            username="kurs_savdo",
            first_name="RULLY User",
            last_name=""
        )
        return user

    is_valid, user_data = verify_telegram_init_data(raw_data)
    if not is_valid or not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user ID in authentication data")

    user = db.get_or_create_user(
        user_id=user_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name", "Haydovchi"),
        last_name=user_data.get("last_name", "")
    )
    return user
