"""
Custom Configurable Test Handler and Launcher for RULLY.
Directs users to the interactive customizable test in RULLY, while also
providing native widget helpers for testing and settings customization.
"""
from typing import Dict, Any
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine
from src.bot.handlers.quiz import render_session_question
from src.bot.keyboards import get_custom_settings_keyboard
from src.bot.strings import get_str
from src.bot.config import WEB_APP_URL

custom_test_router = Router(name="custom_test_router")

# Active user settings cache: {user_id: {"count": int, "time_min": int, "show_answer": bool, "show_expl": bool}}
USER_CUSTOM_SETTINGS: Dict[int, Dict[str, Any]] = {}

def get_user_settings(user_id: int) -> Dict[str, Any]:
    if user_id not in USER_CUSTOM_SETTINGS:
        USER_CUSTOM_SETTINGS[user_id] = {
            "count": 20,
            "time_min": 20,
            "show_answer": True,
            "show_expl": True
        }
    return USER_CUSTOM_SETTINGS[user_id]

def format_settings_widget_card(settings: Dict[str, Any], language: str = "uz_latn") -> str:
    count = settings["count"]
    time_min = settings["time_min"]
    show_ans = settings["show_answer"]
    show_expl = settings["show_expl"]

    if time_min == 0:
        time_str = get_str("settings_unlimited", language)
    else:
        time_str = get_str("settings_minutes", language, mins=time_min)

    ans_str = get_str("settings_yes", language) if show_ans else get_str("settings_no", language)
    expl_str = get_str("settings_expl_yes", language) if show_expl else get_str("settings_expl_no", language)

    title = get_str("settings_widget_title", language)
    desc = get_str("settings_widget_desc", language)

    lbl_count = get_str("settings_label_count", language, count=count)
    lbl_time = get_str("settings_label_time", language, time_str=time_str)
    lbl_ans = get_str("settings_label_answer", language, ans_str=ans_str)
    lbl_expl = get_str("settings_label_expl", language, expl_str=expl_str)

    lines = [
        "╭──────────────────────────────╮",
        f"│  {title}",
        "╰──────────────────────────────╯",
        f"{desc}\n",
        lbl_count,
        lbl_time,
        lbl_ans,
        lbl_expl,
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "<i>Tugmalar orqali parametrlarni o‘zgartiring va start tugmasini bosing:</i>" if language == "uz_latn" else (
            "<i>Тугмалар орқали параметрларни ўзгартиринг ва старт тугмасини босинг:</i>" if language == "uz_cyrl" else
            "<i>Нажимайте на кнопки для изменения параметров и нажмите старт:</i>"
        )
    ]
    return "\n".join(lines)


@custom_test_router.message(Command("test"))
@custom_test_router.message(Command("custom"))
@custom_test_router.message(F.text.in_([
    "🔀 Moslashuvchan test (Aralash)",
    "🔀 Мослашувчан тест (Аралаш)",
    "🔀 Настраиваемый тест (Микс)",
    "⚙️ Aralash test va mavzular",
    "⚙️ Аралаш тест ва мавзулар",
    "⚙️ Настраиваемый тест",
    "⚙️ Moslashuvchan test (Sozlamalar)",
    "⚙️ Мослашувчан тест (Созламалар)",
    "⚙️ Настраиваемый тест (Параметры)",
    "⚙️ Moslashuvchan test",
    "⚙️ Мослашувчан тест"
]))
@custom_test_router.callback_query(F.data == "menu:custom_test")
async def show_custom_test_launcher(event: Message | CallbackQuery, db: BotDatabase):
    user_id = event.from_user.id
    lang = db.get_user_language(user_id)
    if isinstance(event, CallbackQuery):
        await event.answer()

    title = (
        "🔀 <b>Moslashuvchan mashg‘ulot</b>" if lang == "uz_latn" else (
            "🔀 <b>Мослашувчан машғулот</b>" if lang == "uz_cyrl" else
            "🔀 <b>Настраиваемый тренинг</b>"
        )
    )
    desc = (
        "<b>RULLY</b> platformasida test parametrlarini o‘zingizga moslang:\n\n"
        "• Savollar sonini tanlash (10 dan 122 tagacha)\n"
        "• Qulay vaqt chegarasi va nazorat slayderi\n"
        "• Noto‘g‘ri javob berilganda to‘g‘risini ko‘rsatish sozlamasi\n"
        "• Har bir savolga huquqiy asos va ekspert tahlili.\n\n"
        "Mashg‘ulotni boshlash uchun quyidagi tugmani bosing:" if lang == "uz_latn" else (
            "<b>RULLY</b> платформасида тест параметрларини ўзингизга мосланг:\n\n"
            "• Саволлар сонини танлаш (10 дан 122 тагача)\n"
            "• Қулай вақт чегараси ва назорат слайдери\n"
            "• Нотўғри жавоб берилганда тўғрисини кўрсатиш созламаси\n"
            "• Ҳар бир саволга ҳуқуқий асос ва эксперт таҳлили.\n\n"
            "Машғулотни бошлаш учун қуйидаги тугмани босинг:" if lang == "uz_cyrl" else
            "В приложении <b>RULLY</b> вы можете настроить параметры тестирования под себя:\n\n"
            "• Выбор количества вопросов (от 10 до 122)\n"
            "• Удобный слайдер времени и контроль таймера\n"
            "• Настройка показа правильного ответа при ошибке\n"
            "• Официальные статьи ПДД и детальный разбор.\n\n"
            "Для запуска тренинга нажмите кнопку ниже:"
        )
    )
    btn_text = (
        "🚦 Mashg‘ulotni boshlash" if lang == "uz_latn" else (
            "🚦 Машғулотни бошлаш" if lang == "uz_cyrl" else
            "🚦 Начать тренинг"
        )
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=f"{WEB_APP_URL}#tests"))],
        [InlineKeyboardButton(text="🎛️ Bosh menyu" if lang == "uz_latn" else ("🎛️ Бош меню" if lang == "uz_cyrl" else "🎛️ Главное меню"), callback_data="menu:main")]
    ])
    if isinstance(event, CallbackQuery):
        await event.message.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)
    else:
        await event.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)


@custom_test_router.callback_query(F.data.startswith("cfg:cnt:"))
async def cb_change_count(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    cnt_val = int(callback.data.split(":")[2])
    settings = get_user_settings(user_id)
    settings["count"] = cnt_val
    lang = db.get_user_language(user_id)

    await callback.answer()
    text = format_settings_widget_card(settings, lang)
    reply_markup = get_custom_settings_keyboard(settings, lang)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        pass


@custom_test_router.callback_query(F.data.startswith("cfg:time:"))
async def cb_change_time(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    time_val = int(callback.data.split(":")[2])
    settings = get_user_settings(user_id)
    settings["time_min"] = time_val
    lang = db.get_user_language(user_id)

    await callback.answer()
    text = format_settings_widget_card(settings, lang)
    reply_markup = get_custom_settings_keyboard(settings, lang)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        pass


@custom_test_router.callback_query(F.data == "cfg:toggle:ans")
async def cb_toggle_answer(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings["show_answer"] = not settings["show_answer"]
    lang = db.get_user_language(user_id)

    await callback.answer()
    text = format_settings_widget_card(settings, lang)
    reply_markup = get_custom_settings_keyboard(settings, lang)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        pass


@custom_test_router.callback_query(F.data == "cfg:toggle:expl")
async def cb_toggle_expl(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings["show_expl"] = not settings["show_expl"]
    lang = db.get_user_language(user_id)

    await callback.answer()
    text = format_settings_widget_card(settings, lang)
    reply_markup = get_custom_settings_keyboard(settings, lang)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        pass


@custom_test_router.callback_query(F.data == "cfg:action:start")
async def cb_launch_custom_test(callback: CallbackQuery, bot: Bot,
                               product_engine: AvtotestProductEngine, db: BotDatabase):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    lang = db.get_user_language(user_id)
    settings = get_user_settings(user_id)

    await callback.answer()

    # Check for existing active session
    active = db.get_active_session(user_id)
    if active:
        await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ {get_str('active_session_exists', lang)}\n/cancel orqali bekor qilishingiz mumkin.",
            parse_mode="HTML"
        )
        await render_session_question(bot, chat_id, active, product_engine, db)
        return

    # Select questions from canonical bank
    count = settings["count"]
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT canonical_id FROM canonical_questions ORDER BY RANDOM() LIMIT ?", (count,))
        qids = [r["canonical_id"] for r in c.fetchall()]

    if not qids:
        await bot.send_message(chat_id=chat_id, text=get_str("error_generic", lang))
        return

    time_limit_sec = settings["time_min"] * 60

    session = db.create_session(
        user_id=user_id,
        session_type="CUSTOM",
        language=lang,
        question_ids=qids,
        time_limit_seconds=time_limit_sec,
        show_answer=settings["show_answer"],
        show_explanation=settings["show_expl"]
    )

    await render_session_question(bot, chat_id, session, product_engine, db)
