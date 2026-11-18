"""
Telegram Bot Webhook Endpoint for Serverless Deployment (Vercel).
Enables the Telegram Bot to process updates statelessly 24/7 without requiring local daemons.
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, status
from aiogram.types import Update

from src.bot.bot import create_bot_app, setup_bot_commands
from src.bot.config import BOT_TOKEN

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram-webhook", tags=["Telegram Webhook"])

# Lazy-loaded bot app context
_bot = None
_dp = None
_db = None
_engine = None

def get_bot_app():
    global _bot, _dp, _db, _engine
    if _bot is None:
        logger.info("Initializing Bot Webhook Application...")
        _bot, _dp, _db, _engine = create_bot_app()
    return _bot, _dp, _db, _engine


@router.post("")
@router.post("/")
async def telegram_webhook_handler(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Receives incoming webhook updates from Telegram Bot API servers.
    """
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if webhook_secret and x_telegram_bot_api_secret_token != webhook_secret:
        logger.warning("Rejected webhook update due to invalid secret token")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    try:
        data = await request.json()
        bot, dp, _, _ = get_bot_app()
        telegram_update = Update(**data)
        await dp.feed_update(bot=bot, update=telegram_update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error handling Telegram webhook update: {e}", exc_info=True)
        # Always return 200/ok:true to Telegram so it doesn't enter an endless retry loop
        return {"ok": True, "error": str(e)}


@router.get("/info")
async def get_webhook_info():
    """
    Returns current webhook registration details directly from Telegram Bot API.
    """
    try:
        bot, _, _, _ = get_bot_app()
        info = await bot.get_webhook_info()
        return {
            "status": "active" if info.url else "inactive",
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "ip_address": info.ip_address
        }
    except Exception as e:
        logger.error(f"Failed to fetch Telegram webhook info: {e}")
        return {"status": "error", "message": str(e)}
