"""
Main Bot Application Factory & Command Configuration.
"""
import logging
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
        BotCommand(command="menu", description="Boshqaruv panelini ochish"),
        BotCommand(command="exam", description="Davlat nazariy imtihoni (20)"),
        BotCommand(command="test", description="Moslashuvchan test va parametrlar"),
        BotCommand(command="mistakes", description="Xatolar ustida ishlash"),
        BotCommand(command="results", description="Haydovchilik tayyorgarlik indeksi"),
        BotCommand(command="language", description="Tizim tili / Сменить язык"),
        BotCommand(command="help", description="Nizom va imtihon qoidalari")
    ]
    await bot.set_my_commands(commands_uz_latn, scope=BotCommandScopeDefault(), language_code="uz")

    # 2. Russian
    commands_ru = [
        BotCommand(command="start", description="Запуск платформы RULLY"),
        BotCommand(command="menu", description="Панель управления"),
        BotCommand(command="exam", description="Государственный экзамен (20)"),
        BotCommand(command="test", description="Настраиваемый тренинг"),
        BotCommand(command="mistakes", description="Диагностика ошибок"),
        BotCommand(command="results", description="Индекс готовности водителя"),
        BotCommand(command="language", description="Сменить язык интерфейса"),
        BotCommand(command="help", description="Регламент и правила")
    ]
    await bot.set_my_commands(commands_ru, scope=BotCommandScopeDefault(), language_code="ru")

    # Fallback default
    await bot.set_my_commands(commands_uz_latn, scope=BotCommandScopeDefault())

    # Configure Telegram Menu Button to open RULLY
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🛞 RULLY",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
        logger.info("Bot MenuButtonWebApp set successfully")
    except Exception as e:
        logger.warning(f"Could not set MenuButtonWebApp (using default menu): {e}")

    logger.info("Bot commands successfully registered in multiple languages")

def create_bot_app() -> tuple[Bot, Dispatcher, BotDatabase, AvtotestProductEngine]:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    db = BotDatabase(db_path=DB_PATH)
    product_engine = AvtotestProductEngine(db_path=DB_PATH)

    # Attach middlewares
    dp.update.middleware(DependencyInjectionMiddleware(db=db, product_engine=product_engine))
    dp.update.middleware(SimpleRateLimitMiddleware(limit_seconds=0.15))

    # Register handlers
    dp.include_router(main_router)

    return bot, dp, db, product_engine
