"""
Main Bot Application Factory & Command Configuration.
"""
import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo

from src.bot.config import BOT_TOKEN, DB_PATH, WEB_APP_URL
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine
from src.bot.handlers import main_router
from src.bot.middleware import DependencyInjectionMiddleware, SimpleRateLimitMiddleware

logger = logging.getLogger(__name__)

async def setup_bot_commands(bot: Bot):
    """
    Registers native localized Telegram command menus.
    """
    # 1. Default / Uzbek Latin
    commands_uz_latn = [
        BotCommand(command="start", description="RULLY platformasini ishga tushirish"),
        BotCommand(command="menu", description="Bosh menyuni ko‘rsatish"),
        BotCommand(command="exam", description="Davlat imtihoni (20 ta savol)"),
        BotCommand(command="srs", description="Aqlli Takrorlash (SM-2)"),
        BotCommand(command="bilet", description="Rasmiy biletlar (1–67)"),
        BotCommand(command="test", description="Aralash test va sozlamalar"),
        BotCommand(command="mistakes", description="Xatolar banki"),
        BotCommand(command="results", description="Tayyorgarlik darajasi"),
        BotCommand(command="pro", description="RULLY PRO obuna (Stars ⭐ / HUMO)"),
        BotCommand(command="language", description="Tilni o‘zgartirish / Сменить язык"),
        BotCommand(command="help", description="Yordam va bo‘limlar")
    ]
    await bot.set_my_commands(commands_uz_latn, scope=BotCommandScopeDefault(), language_code="uz")

    # 2. Russian
    commands_ru = [
        BotCommand(command="start", description="Запустить платформу RULLY"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="exam", description="Гос. экзамен (20 вопросов)"),
        BotCommand(command="srs", description="Умное повторение (SM-2)"),
        BotCommand(command="bilet", description="Официальные билеты (1–67)"),
        BotCommand(command="test", description="Настраиваемый тест"),
        BotCommand(command="mistakes", description="Банк ошибок"),
        BotCommand(command="results", description="Индекс готовности"),
        BotCommand(command="pro", description="Подписка RULLY PRO (Stars ⭐ / HUMO)"),
        BotCommand(command="language", description="Сменить язык"),
        BotCommand(command="help", description="Помощь и разделы")
    ]
    await bot.set_my_commands(commands_ru, scope=BotCommandScopeDefault(), language_code="ru")

    # Fallback default
    await bot.set_my_commands(commands_uz_latn, scope=BotCommandScopeDefault())

    # Configure Telegram Menu Button to open RULLY
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚗 RULLY",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
        logger.info("Bot MenuButtonWebApp set successfully")
    except Exception as e:
        logger.warning(f"Could not set MenuButtonWebApp (using default menu): {e}")

    logger.info("Bot commands successfully registered in multiple languages")

def create_bot_app(product_engine: Optional[AvtotestProductEngine] = None) -> tuple[Bot, Dispatcher, BotDatabase, AvtotestProductEngine]:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    db = BotDatabase(db_path=DB_PATH)
    engine_inst = product_engine if product_engine is not None else AvtotestProductEngine(db_path=DB_PATH)

    # Attach middlewares
    dp.update.middleware(DependencyInjectionMiddleware(db=db, product_engine=engine_inst))
    dp.update.middleware(SimpleRateLimitMiddleware(limit_seconds=0.15))

    # Register handlers
    dp.include_router(main_router)

    return bot, dp, db, engine_inst
