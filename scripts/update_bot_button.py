import asyncio
import os
from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://rully-rully4.vercel.app")

async def update_button():
    bot = Bot(token=BOT_TOKEN)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="AvtoTest O'tish 🚗",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    print(f"Bot menu button successfully updated to: {WEB_APP_URL}")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(update_button())
