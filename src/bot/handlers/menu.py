"""
Main Menu and Navigation Handlers.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.bot.keyboards import (
    get_main_menu_keyboard,
    get_language_keyboard,
    get_help_sections_keyboard,
)
from src.bot.strings import get_str
from src.bot.config import WEB_APP_URL

menu_router = Router(name="menu_router")

@menu_router.message(Command("menu"))
@menu_router.message(F.text.in_(["🏠 Menyu", "🏠 Меню"]))
async def show_menu_cmd(message: Message, db: BotDatabase):
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    caption = f"{get_str('welcome_title', lang)}\n\n{get_str('welcome_text', lang)}"
    await message.answer(
        text=caption,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(lang)
    )

@menu_router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()
    caption = f"{get_str('welcome_title', lang)}\n\n{get_str('welcome_text', lang)}"
    try:
        await callback.message.edit_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(lang)
        )
    except Exception:
        await callback.message.answer(
            text=caption,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(lang)
        )

@menu_router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()

    lang_names = {
        "uz_latn": "O‘zbekcha (Lotin)",
        "uz_cyrl": "Ўзбекча (Кирилл)",
        "ru": "Русский"
    }
    curr_lang_name = lang_names.get(lang, lang)

    if lang == "uz_cyrl":
        text = (
            "⚙️ <b>СОЗЛАМАЛАР</b>\n\n"
            f"• Ҳозирги тил: <b>{curr_lang_name}</b>\n\n"
            "Интерфейс тилини ўзгартириш учун қуйидаги тугмалардан бирини босинг:"
        )
    elif lang == "ru":
        text = (
            "⚙️ <b>НАСТРОЙКИ</b>\n\n"
            f"• Текущий язык: <b>{curr_lang_name}</b>\n\n"
            "Для смены языка интерфейса нажмите на одну из кнопок ниже:"
        )
    else:
        text = (
            "⚙️ <b>SOZLAMALAR</b>\n\n"
            f"• Hozirgi til: <b>{curr_lang_name}</b>\n\n"
            "Interfeys tilini o‘zgartirish uchun quyidagi tugmalardan birini bosing:"
        )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_language_keyboard()
    )

@menu_router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()
    kb = get_help_sections_keyboard(lang)
    try:
        await callback.message.edit_text(
            text=get_str("help_text", lang),
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        await callback.message.answer(
            text=get_str("help_text", lang),
            parse_mode="HTML",
            reply_markup=kb
        )
