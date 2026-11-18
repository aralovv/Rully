"""
Production Runner for Avtotest Uzbekistan Telegram Bot.
"""
import sys
import os
import asyncio
import logging
import argparse

sys.path.insert(0, os.path.abspath("c:/Users/Администратор/AvtoTest"))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.bot.bot import create_bot_app, setup_bot_commands
from src.bot.config import BOT_NAME, BOT_VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_bot")

async def check_health_cmd():
    print(f"=== {BOT_NAME} v{BOT_VERSION} Health Check ===")
    bot, dp, db, product_engine = create_bot_app()
    
    me = await bot.get_me()
    print(f"✅ Telegram API Connected: @{me.username} ({me.first_name}, ID: {me.id})")
    
    stats = db.get_admin_stats()
    print(f"✅ Database Status: {stats['status']}")
    print(f"   • Canonical Questions: {stats['canonical_questions']}")
    print(f"   • Canonical Translations: {stats['canonical_translations']}")
    print(f"   • Registered Users: {stats['total_users']}")
    
    cats = product_engine.get_categories("uz_latn")
    print(f"✅ Categories loaded: {len(cats)} categories")
    print("All health checks PASSED successfully!")
    await bot.session.close()

async def main():
    parser = argparse.ArgumentParser(description="Avtotest Telegram Bot Runner")
    parser.add_argument("--health", action="store_true", help="Run health check and exit")
    args = parser.parse_args()

    if args.health:
        await check_health_cmd()
        return

    logger.info(f"Starting {BOT_NAME} v{BOT_VERSION}...")
    bot, dp, db, product_engine = create_bot_app()

    # Drop any pending updates on startup to prevent backlog spamming
    await bot.delete_webhook(drop_pending_updates=True)

    # Register command menus
    await setup_bot_commands(bot)

    me = await bot.get_me()
    logger.info(f"Bot @{me.username} is running in polling mode. Press Ctrl+C to stop.")

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Closing bot session...")
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped cleanly.")
