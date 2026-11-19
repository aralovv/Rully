"""
Start, Onboarding, Language Selection, and Help Handlers.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command, CommandObject
from src.bot.database import BotDatabase
from src.bot.keyboards import get_language_keyboard, get_main_menu_keyboard, get_main_reply_keyboard
from src.bot.strings import get_str
from src.bot.config import WEB_APP_URL

start_router = Router(name="start_router")

@start_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, db: BotDatabase):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    user = db.get_or_create_user(
        user_id=user_id, username=username,
        first_name=first_name, last_name=last_name
    )
    lang = user["language"]

    # Deep linking support
    args = (command.args or "").strip().lower()
    if args == "amaliy":
        amaliy_title = "🛞 <b>RULLY Amaliy Imtihon</b>" if lang == "uz_latn" else ("🛞 <b>RULLY Амалий Имтиҳон</b>" if lang == "uz_cyrl" else "🛞 <b>RULLY Практический Экзамен</b>")
        amaliy_text = (
            "10 ta amaliy mashg‘ulot, avtodrom cheklisti va vaziyatli savollardan foydalanish uchun RULLY ilovasini oching!" if lang == "uz_latn" else (
                "10 та амалий машғулот, автодром чеклисти ва вазиятли саволлардан фойдаланиш учун RULLY иловасини очинг!" if lang == "uz_cyrl" else
                "Для доступа к 10 практическим упражнениям, чек-листу автодрома и разбору ситуаций откройте приложение RULLY!"
            )
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚧 Avtodrom va amaliyotni ochish", web_app=WebAppInfo(url=f"{WEB_APP_URL}#amaliy"))]
        ])
        await message.answer(f"{amaliy_title}\n\n{amaliy_text}", parse_mode="HTML", reply_markup=kb)
        return

    # Check if user has already selected a language (only ask once on first launch)
    if not db.has_user_selected_language(user_id):
        onboarding_text = (
            "🛞 <b>RULLY</b>\n\n"
            "Iltimos, interfeys tilini tanlang:\n"
            "Илтимос, интерфейс тилини танланг:\n"
            "Пожалуйста, выберите язык интерфейса:"
        )
        await message.answer(
            text=onboarding_text,
            parse_mode="HTML",
            reply_markup=get_language_keyboard()
        )
        return

    # Returning user who already has a chosen language -> show welcome and main menu directly
    welcome_title = get_str("welcome_title", lang)
    welcome_text = get_str("welcome_text", lang)
    caption = f"{welcome_title}\n\n{welcome_text}"

    await message.answer(
        text=caption,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(lang)
    )

@start_router.callback_query(F.data.startswith("lang:"))
async def cb_select_language(callback: CallbackQuery, db: BotDatabase):
    user_id = callback.from_user.id
    selected_lang = callback.data.split(":")[1]

    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"

    # set_user_language records language and sets is_language_selected = 1
    db.set_user_language(user_id, selected_lang)
    await callback.answer()

    # Confirm and show main menu directly
    confirm_text = get_str("language_selected", selected_lang)
    welcome_title = get_str("welcome_title", selected_lang)
    welcome_text = get_str("welcome_text", selected_lang)
    full_text = f"{confirm_text}\n\n{welcome_title}\n\n{welcome_text}"

    try:
        await callback.message.edit_text(
            text=full_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(selected_lang)
        )
    except Exception:
        await callback.message.answer(
            text=full_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(selected_lang)
        )

@start_router.message(F.text.in_(["🌐 Til", "🌐 Тил", "🌐 Язык", "🗺️ Til", "🗺️ Тил", "🗺️ Язык", "🗺️ Tizim tili", "🗺️ Тизим тили", "🗺️ Язык интерфейса"]))
@start_router.message(Command("language"))
async def cmd_language(message: Message, db: BotDatabase):
    lang = db.get_user_language(message.from_user.id)
    lang_prompt = (
        "🗺️ <b>Interfeys tilini tanlang:</b>" if lang == "uz_latn" else (
            "🗺️ <b>Интерфейс тилини танланг:</b>" if lang == "uz_cyrl" else
            "🗺️ <b>Выберите язык интерфейса:</b>"
        )
    )
    await message.answer(
        text=lang_prompt,
        parse_mode="HTML",
        reply_markup=get_language_keyboard()
    )

@start_router.message(F.text.in_([
    "ℹ️ Yordam", "ℹ️ Ёрдам", "ℹ️ Помощь",
    "🔰 Yordam", "🔰 Ёрдам", "🔰 Помощь",
    "🔰 Nizom va yordam", "🔰 Низом ва ёрдам", "🔰 Регламент и помощь",
    "🔰 Nizom va qoidalar", "🔰 Низом ва қоидалар", "🔰 Регламент и правила"
]))
@start_router.message(Command("help"))
async def cmd_help(message: Message, db: BotDatabase):
    lang = db.get_user_language(message.from_user.id)
    await message.answer(
        text=get_str("help_text", lang),
        parse_mode="HTML"
    )

@start_router.message(Command("cancel"))
async def cmd_cancel(message: Message, db: BotDatabase):
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    active = db.get_active_session(user_id)
    if active:
        db.finish_session(active["session_id"], status="ABORTED")
        await message.answer(get_str("session_cancelled", lang), parse_mode="HTML")
    else:
        await message.answer(get_str("menu_title", lang), parse_mode="HTML", reply_markup=get_main_menu_keyboard(lang))

@start_router.message(Command("pro"))
@start_router.message(Command("obuna"))
async def cmd_subscription(message: Message, db: BotDatabase):
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    sub = db.get_user_subscription(user_id)

    if lang == "uz_latn":
        status_line = f"Sizning tarifingiz: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" ({sub['days_left']} kun qoldi)"
        text = (
            f"👑 <b>RULLY PRO Obuna Tizimi</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Mavjud PRO tariflar:</b>\n"
            f"• <b>14 kunlik (2 hafta)</b> — 14 000 so‘m\n"
            f"• <b>30 kunlik (1 oy)</b> — 25 000 so‘m (⭐ Eng ommabop)\n\n"
            f"<b>PRO imkoniyatlari:</b>\n"
            f"✅ Davlat nazariy imtihoni (20 savol / 25 daqiqa)\n"
            f"✅ Xatolar ustida ishlash (Diagnostika)\n"
            f"✅ AI Ustoz (24/7 shaxsiy intellektual instruktor)\n"
            f"✅ To‘liq imtihon shpargalkasi va meʼyorlar\n"
            f"✅ Aniq statistika va haydovchilik indeksi"
        )
        btn_text = "💳 Obunani faollashtirish (Profil)"
    elif lang == "uz_cyrl":
        status_line = f"Сизнинг тарифингиз: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" ({sub['days_left']} кун қолди)"
        text = (
            f"👑 <b>RULLY PRO Обуна Тизими</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Мавжуд PRO тарифлар:</b>\n"
            f"• <b>14 кунлик (2 ҳафта)</b> — 14 000 сўм\n"
            f"• <b>30 кунлик (1 ой)</b> — 25 000 сўм (⭐ Энг оммабоп)\n\n"
            f"<b>PRO имкониятлари:</b>\n"
            f"✅ Давлат назарий имтиҳони (20 савол / 25 дақиқа)\n"
            f"✅ Хатолар устида ишлаш (Диагностика)\n"
            f"✅ AI Устоз (24/7 шахсий интеллектуал инструктор)\n"
            f"✅ Тўлиқ имтиҳон шпаргалкаси ва меъёрлар\n"
            f"✅ Аниқ статистика ва ҳайдовчилик индекси"
        )
        btn_text = "💳 Обунани фаоллаштириш (Профиль)"
    else:
        status_line = f"Ваш тариф: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" (осталось {sub['days_left']} дн.)"
        text = (
            f"👑 <b>Подписка RULLY PRO</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Доступные PRO тарифы:</b>\n"
            f"• <b>14 дней (2 недели)</b> — 14 000 сум\n"
            f"• <b>30 дней (1 месяц)</b> — 25 000 сум (⭐ Хит продаж)\n\n"
            f"<b>Возможности PRO:</b>\n"
            f"✅ Государственный экзамен (20 вопросов / 25 мин)\n"
            f"✅ Диагностика и работа над ошибками\n"
            f"✅ AI Инструктор (24/7 персональный разбор ситуаций)\n"
            f"✅ Полная шпаргалка и нормативы ПДД\n"
            f"✅ Подробная статистика и индекс готовности"
        )
        btn_text = "💳 Активировать подписку (Профиль)"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=f"{WEB_APP_URL}#profile"))]
    ])
    await message.answer(text=text, parse_mode="HTML", reply_markup=kb)
