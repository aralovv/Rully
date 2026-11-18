"""
Registers the Telegram Webhook with Telegram Bot API to point to Vercel Serverless Gateway.
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.bot.config import BOT_TOKEN
from src.bot.bot import setup_bot_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("set_webhook")

WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "https://rully-rully4.vercel.app/api/telegram-webhook")
SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET")

async def main():
    logger.info(f"Connecting to Telegram Bot API with token {BOT_TOKEN[:10]}...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    try:
        # 1. Setup localized commands
        logger.info("Setting bot commands and WebApp menu button...")
        await setup_bot_commands(bot)

        # 2. Set webhook
        logger.info(f"Setting webhook URL to: {WEBHOOK_URL}")
        kwargs = {
            "url": WEBHOOK_URL,
            "drop_pending_updates": True,
            "max_connections": 100
        }
        if SECRET_TOKEN:
            kwargs["secret_token"] = SECRET_TOKEN

        res = await bot.set_webhook(**kwargs)
        logger.info(f"Set webhook result: {res}")

        # 3. Check webhook info
        info = await bot.get_webhook_info()
        logger.info("Current Telegram Webhook Info:")
        logger.info(f"  URL: {info.url}")
        logger.info(f"  Pending update count: {info.pending_update_count}")
        logger.info(f"  Last error date: {info.last_error_date}")
        logger.info(f"  Last error message: {info.last_error_message}")
        logger.info(f"  Max connections: {info.max_connections}")

    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
