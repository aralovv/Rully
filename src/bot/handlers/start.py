"""
Start, Onboarding, Language Selection, and Help Handlers.
"""
import re
from typing import Dict, Any, Optional, Tuple
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command, CommandObject
from src.bot.database import BotDatabase
from src.bot.keyboards import (
    get_language_keyboard,
    get_main_menu_keyboard,
    get_main_reply_keyboard,
    get_deep_link_card_keyboard,
)
from src.bot.strings import get_str
from src.bot.config import WEB_APP_URL

start_router = Router(name="start_router")

_DEEP_LINK_CARDS: Dict[str, Dict[str, Any]] = {
    "amaliy": {
        "route": "amaliy",
        "title": {
            "uz_latn": "🚗 <b>RULLY Amaliy Tayyorgarlik</b>",
            "uz_cyrl": "🚗 <b>RULLY Амалий Тайёргарлик</b>",
            "ru": "🚗 <b>RULLY Практическая Подготовка</b>",
        },
        "desc": {
            "uz_latn": "10 ta amaliy haydash darsligi va jarimalar ma'lumotnomasidan foydalanish uchun RULLY'ni oching!",
            "uz_cyrl": "10 та амалий ҳайдаш дарслиги ва жарималар маълумотномасидан фойдаланиш учун RULLY'ни очинг!",
            "ru": "Для доступа к 10 обучающим модулям вождения и справочнику штрафов откройте RULLY!",
        },
        "app_btn": {
            "uz_latn": "🚀 Amaliy mashqlarni ochish",
            "uz_cyrl": "🚀 Амалий машқларни очиш",
            "ru": "🚀 Открыть практику",
        },
    },
    "exam": {
        "route": "exam",
        "title": {
            "uz_latn": "🏆 <b>Davlat Nazariy Imtihoni (VMQ 408)</b>",
            "uz_cyrl": "🏆 <b>Давлат Назарий Имтиҳони (ВМҚ 408)</b>",
            "ru": "🏆 <b>Государственный Теоретический Экзамен</b>",
        },
        "desc": {
            "uz_latn": "20 ta savol • 25 daqiqa • o‘tish talabi kamida 18 ta to‘g‘ri javob (F1–F4 tezkor klaviatura).",
            "uz_cyrl": "20 та савол • 25 дақиқа • ўтиш талаби камида 18 та тўғри жавоб.",
            "ru": "20 вопросов • 25 минут • проходной балл не менее 18 правильных ответов.",
        },
        "app_btn": {
            "uz_latn": "🏆 RULLY'da imtihon boshlash",
            "uz_cyrl": "🏆 RULLY'да имтиҳон бошлаш",
            "ru": "🏆 Начать экзамен в RULLY",
        },
    },
    "signs": {
        "route": "signs",
        "title": {
            "uz_latn": "🛑 <b>O‘zbekiston Yo‘l Belgilari (VMQ 172)</b>",
            "uz_cyrl": "🛑 <b>Ўзбекистон Йўл Белгилари (ВМҚ 172)</b>",
            "ru": "🛑 <b>Дорожные Знаки Узбекистана (ПКМ 172)</b>",
        },
        "desc": {
            "uz_latn": "Barcha rasmiy yo‘l belgilari guruhlari va qisqa izohlarini bir joyda o‘rganing.",
            "uz_cyrl": "Барча расмий йўл белгилари гуруҳлари ва қисқа изоҳларини бир жойда ўрганинг.",
            "ru": "Изучайте все официальные группы дорожных знаков и их значения в одном месте.",
        },
        "app_btn": {
            "uz_latn": "🛑 Yo‘l belgilarini ochish",
            "uz_cyrl": "🛑 Йўл белгиларини очиш",
            "ru": "🛑 Открыть дорожные знаки",
        },
    },
    "rules": {
        "route": "rules",
        "title": {
            "uz_latn": "📜 <b>Rasmiy YHQ Qonuni (VMQ 172)</b>",
            "uz_cyrl": "📜 <b>Расмий ЙҲҚ Қонуни (ВМҚ 172)</b>",
            "ru": "📜 <b>Официальные ПДД Узбекистана (ПКМ 172)</b>",
        },
        "desc": {
            "uz_latn": "VMQ 172 boblari, bandlari, tezlik me'yorlari va shpargalka jadvallari.",
            "uz_cyrl": "ВМҚ 172 боблари, бандлари, тезлик меъёрлари ва шпаргалка жадваллари.",
            "ru": "Главы ПКМ 172, пункты ПДД, скоростные ограничения и справочник.",
        },
        "app_btn": {
            "uz_latn": "📜 Qonun va jadvallarni ochish",
            "uz_cyrl": "📜 Қонун ва жадвалларни очиш",
            "ru": "📜 Открыть справочник ПДД",
        },
    },
    "ai": {
        "route": "ai",
        "title": {
            "uz_latn": "🤖 <b>AI Ustoz — YHQ Ekspert Yordamchisi</b>",
            "uz_cyrl": "🤖 <b>AI Устоз — ЙҲҚ Эксперт Ёрдамчиси</b>",
            "ru": "🤖 <b>AI Наставник — Эксперт по ПДД</b>",
        },
        "desc": {
            "uz_latn": "Murakkab chorrahalar, belgilar va xato qilingan savollar bo‘yicha shaxsiy tahlil oling.",
            "uz_cyrl": "Мураккаб чорраҳалар, белгилар ва хато қилинган саволлар бўйича шахсий таҳлил олинг.",
            "ru": "Получайте персональные разборы сложных перекрёстков, знаков и ваших ошибок.",
        },
        "app_btn": {
            "uz_latn": "🤖 AI Ustozni ochish",
            "uz_cyrl": "🤖 AI Устозни очиш",
            "ru": "🤖 Открыть AI Наставника",
        },
    },
    "mistakes": {
        "route": "mistakes",
        "title": {
            "uz_latn": "📚 <b>Xatolar Banki</b>",
            "uz_cyrl": "📚 <b>Хатолар Банки</b>",
            "ru": "📚 <b>Банк Ошибок</b>",
        },
        "desc": {
            "uz_latn": "Oldin adashgan savollaringizni qayta ishlab mustahkamlang.",
            "uz_cyrl": "Олдин адашган саволларингизни қайта ишлаб мустаҳкамланг.",
            "ru": "Отработайте ранее допущенные ошибки до уверенного результата.",
        },
        "app_btn": {
            "uz_latn": "🚗 RULLY'da ko‘rish",
            "uz_cyrl": "🚗 RULLY'да кўриш",
            "ru": "🚗 Открыть в RULLY",
        },
        "inline_cb": "menu:mistakes",
        "inline_btn": {
            "uz_latn": "📚 Botda xatolarni ishlash",
            "uz_cyrl": "📚 Ботда хатоларни ишлаш",
            "ru": "📚 Решать ошибки в боте",
        },
    },
    "profile": {
        "route": "profile",
        "title": {
            "uz_latn": "📊 <b>Tayyorgarlik Indeksi va Profil</b>",
            "uz_cyrl": "📊 <b>Тайёргарлик Индекси ва Профил</b>",
            "ru": "📊 <b>Индекс Готовности и Профиль</b>",
        },
        "desc": {
            "uz_latn": "Shaxsiy tayyorgarlik ko‘rsatkichi, kunlik maqsad va RULLY PRO boshqaruvi.",
            "uz_cyrl": "Шахсий тайёргарлик кўрсаткичи, кунлик мақсад ва RULLY PRO бошқаруви.",
            "ru": "Персональный индекс готовности, дневная цель и управление подпиской RULLY PRO.",
        },
        "app_btn": {
            "uz_latn": "📊 Profilni ochish",
            "uz_cyrl": "📊 Профилни очиш",
            "ru": "📊 Открыть профиль",
        },
        "inline_cb": "menu:results",
        "inline_btn": {
            "uz_latn": "📈 Botda statistikani ko‘rish",
            "uz_cyrl": "📈 Ботда статистикани кўриш",
            "ru": "📈 Посмотреть статистику в боте",
        },
    },
    "tests": {
        "route": "tests",
        "title": {
            "uz_latn": "📖 <b>Tayyorlov Markazi</b>",
            "uz_cyrl": "📖 <b>Тайёрлов Маркази</b>",
            "ru": "📖 <b>Центр Подготовки</b>",
        },
        "desc": {
            "uz_latn": "41 ta mavzu, 67 ta rasmiy bilet, Aqlli Takrorlash va YHQ ma'lumotnomasi.",
            "uz_cyrl": "41 та мавзу, 67 та расмий билет, Ақлли Такрорлаш ва ЙҲҚ маълумотномаси.",
            "ru": "41 тема, 67 официальных билетов, Умное повторение и справочник ПДД.",
        },
        "app_btn": {
            "uz_latn": "📖 Tayyorlov bo‘limini ochish",
            "uz_cyrl": "📖 Тайёрлов бўлимини очиш",
            "ru": "📖 Открыть раздел подготовки",
        },
        "inline_cb": "menu:bilets",
        "inline_btn": {
            "uz_latn": "🎫 Botda bilet tanlash",
            "uz_cyrl": "🎫 Ботда билет танлаш",
            "ru": "🎫 Выбрать билет в боте",
        },
    },
}

_DEEP_LINK_ALIASES = {
    "belgilar": "signs",
    "qoidalar": "rules",
    "law": "rules",
    "ustoz": "ai",
    "xatolar": "mistakes",
    "stats": "profile",
    "topics": "tests",
    "tickets": "tests",
    "bilets": "tests",
}


def build_deep_link_response(
    raw_arg: str,
    lang: str,
    db: BotDatabase,
    user_id: int,
) -> Optional[Tuple[str, Any]]:
    """Resolves /start deep-link payloads into rich localized Mini App + inline quiz cards."""
    arg = (raw_arg or "").strip().lower()
    if not arg:
        return None
    arg = _DEEP_LINK_ALIASES.get(arg, arg)

    # 1. SM-2 Aqlli Takrorlash deep link (/start srs | /start takrorlash | /start adaptive)
    if arg in ("srs", "takrorlash", "adaptive"):
        srs_data = db.get_srs_queue_summary(user_id, limit=10)
        summary = srs_data.get("summary", {})
        text = get_str(
            "srs_intro",
            lang,
            due_now=summary.get("due_now_count", 0),
            mastered=summary.get("mastered_count", 0),
            tracked=summary.get("tracked_count", 0),
        )
        app_btn = {
            "uz_latn": "🚀 Mini App: Aqlli Takrorlash",
            "uz_cyrl": "🚀 Mini App: Ақлли Такрорлаш",
            "ru": "🚀 Mini App: Умное повторение",
        }.get(lang, "🚀 Mini App: Aqlli Takrorlash")
        inline_btn = {
            "uz_latn": "🧠 Botda takrorlash (SM-2)",
            "uz_cyrl": "🧠 Ботда такрорлаш (SM-2)",
            "ru": "🧠 Повторять в боте (SM-2)",
        }.get(lang, "🧠 Botda takrorlash (SM-2)")
        return text, get_deep_link_card_keyboard("srs", app_btn, lang, inline_callback="menu:srs", inline_btn_text=inline_btn)

    # 2. Specific Bilet deep link (/start bilet_5 | /start bilet-5 | /start ticket_5)
    m_bilet = re.match(r"^(?:bilet|ticket)[_-]?(\d{1,3})$", arg)
    if m_bilet:
        bilet_no = int(m_bilet.group(1))
        if 1 <= bilet_no <= 100:
            title = {
                "uz_latn": f"🎫 <b>Rasmiy Bilet #{bilet_no}</b>",
                "uz_cyrl": f"🎫 <b>Расмий Билет #{bilet_no}</b>",
                "ru": f"🎫 <b>Официальный Билет №{bilet_no}</b>",
            }.get(lang, f"🎫 <b>Rasmiy Bilet #{bilet_no}</b>")
            desc = {
                "uz_latn": f"Bilet #{bilet_no} savollarini hoziroq Telegram Botda yoki RULLY Mini App ichida yeching!",
                "uz_cyrl": f"Билет #{bilet_no} саволларини ҳозироқ Telegram Ботда ёки RULLY Mini App ичида ечинг!",
                "ru": f"Решайте вопросы билета №{bilet_no} прямо в Telegram-боте или в приложении RULLY!",
            }.get(lang, f"Bilet #{bilet_no} savollarini yechishni boshlang:")
            app_btn = {
                "uz_latn": f"🚗 Mini App: Bilet #{bilet_no}",
                "uz_cyrl": f"🚗 Mini App: Билет #{bilet_no}",
                "ru": f"🚗 Mini App: Билет №{bilet_no}",
            }.get(lang, f"🚗 Mini App: Bilet #{bilet_no}")
            inline_btn = {
                "uz_latn": f"📝 Botda Bilet #{bilet_no} ni boshlash",
                "uz_cyrl": f"📝 Ботда Билет #{bilet_no} ни бошлаш",
                "ru": f"📝 Начать Билет №{bilet_no} в боте",
            }.get(lang, f"📝 Botda Bilet #{bilet_no} ni boshlash")
            return f"{title}\n\n{desc}", get_deep_link_card_keyboard(
                f"bilet_{bilet_no}", app_btn, lang, inline_callback=f"bilet:start:{bilet_no}", inline_btn_text=inline_btn
            )

    # 3. Static table-driven cards
    card = _DEEP_LINK_CARDS.get(arg)
    if card:
        title = card["title"].get(lang, card["title"]["uz_latn"])
        desc = card["desc"].get(lang, card["desc"]["uz_latn"])
        app_btn = card["app_btn"].get(lang, card["app_btn"]["uz_latn"])
        inline_cb = card.get("inline_cb")
        inline_btn = card["inline_btn"].get(lang, card["inline_btn"]["uz_latn"]) if card.get("inline_btn") else None
        return f"{title}\n\n{desc}", get_deep_link_card_keyboard(
            card["route"], app_btn, lang, inline_callback=inline_cb, inline_btn_text=inline_btn
        )

    return None

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
    deep_res = build_deep_link_response(command.args or "", lang, db, user_id)
    if deep_res:
        text, kb = deep_res
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    # Check if user has already selected a language (only ask once on first launch)
    if not db.has_user_selected_language(user_id):
        onboarding_text = (
            "🚗 <b>RULLY</b>\n\n"
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

@start_router.message(F.text.in_(["🌐 Til", "🌐 Тил", "🌐 Язык"]))
@start_router.message(Command("language"))
async def cmd_language(message: Message, db: BotDatabase):
    lang = db.get_user_language(message.from_user.id)
    lang_prompt = (
        "🌐 <b>Interfeys tilini tanlang:</b>" if lang == "uz_latn" else (
            "🌐 <b>Интерфейс тилини танланг:</b>" if lang == "uz_cyrl" else
            "🌐 <b>Выберите язык интерфейса:</b>"
        )
    )
    await message.answer(
        text=lang_prompt,
        parse_mode="HTML",
        reply_markup=get_language_keyboard()
    )

@start_router.message(F.text.in_(["ℹ️ Yordam", "ℹ️ Ёрдам", "ℹ️ Помощь"]))
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

    try:
        from src.payments.order_manager import list_active_subscription_plans
        plans = list_active_subscription_plans()
    except Exception:
        plans = []
    if not plans:
        plans = [
            {"id": "pro_14", "name": "14 kunlik PRO", "price_formatted": "14 000 so‘m", "stars_price": 78},
            {"id": "pro_30", "name": "30 kunlik PRO", "price_formatted": "25 000 so‘m", "stars_price": 139},
        ]

    plan_lines = "\n".join(
        f"• <b>{pl['name']}</b> — {pl['price_formatted']} · <b>{pl['stars_price']} ⭐ Stars</b>"
        for pl in plans
    )

    if lang == "uz_latn":
        status_line = f"Sizning tarifingiz: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" ({sub['days_left']} kun qoldi)"
        text = (
            f"👑 <b>RULLY PRO Obuna Tizimi</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Mavjud PRO tariflar:</b>\n"
            f"{plan_lines}\n\n"
            f"<b>PRO imkoniyatlari:</b>\n"
            f"✅ Cheksiz Davlat Imtihoni (20 savol / 25 daqiqa)\n"
            f"✅ AI Ustoz 3.0 (kuniga 100 tagacha tahlil) va 7 kunlik o‘quv reja\n"
            f"✅ Rasmiy VMQ 172 qonun matni va 10 ta amaliy mashq moduli\n"
            f"✅ Telegram Stars (⭐) orqali 1 soniyada faollashuv"
        )
        btn_webapp = "💳 Karta (HUMO) / Mini App orqali"
        stars_prefix = "⭐ Stars:"
    elif lang == "uz_cyrl":
        status_line = f"Сизнинг тарифингиз: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" ({sub['days_left']} кун қолди)"
        text = (
            f"👑 <b>RULLY PRO Обуна Тизими</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Мавжуд PRO тарифлар:</b>\n"
            f"{plan_lines}\n\n"
            f"<b>PRO имкониятлари:</b>\n"
            f"✅ Чексиз Давлат Имтиҳони (20 савол / 25 дақиқа)\n"
            f"✅ AI Устоз 3.0 (кунига 100 тагача таҳлил) ва 7 кунлик ўқув режа\n"
            f"✅ Расмий ВМҚ 172 қонун матни ва 10 та амалий машқ модули\n"
            f"✅ Telegram Stars (⭐) орқали бир зумда фаоллашув"
        )
        btn_webapp = "💳 Карта (HUMO) / Mini App орқали"
        stars_prefix = "⭐ Stars:"
    else:
        status_line = f"Ваш тариф: <b>{sub['tier_name']}</b>"
        if sub["is_pro"]:
            status_line += f" (осталось {sub['days_left']} дн.)"
        text = (
            f"👑 <b>Подписка RULLY PRO</b>\n\n"
            f"{status_line}\n\n"
            f"<b>Доступные PRO тарифы:</b>\n"
            f"{plan_lines}\n\n"
            f"<b>Возможности PRO:</b>\n"
            f"✅ Безлимитный Госэкзамен (20 вопросов / 25 мин)\n"
            f"✅ AI Наставник 3.0 (до 100 разборов в день) и 7-дневный план\n"
            f"✅ Официальный закон ПКМ 172 и 10 практических модулей\n"
            f"✅ Мгновенная оплата через Telegram Stars (⭐)"
        )
        btn_webapp = "💳 Карта (HUMO) / Через Mini App"
        stars_prefix = "⭐ Stars:"

    rows = [
        [InlineKeyboardButton(text=f"{stars_prefix} {pl['name']} — {pl['stars_price']} ⭐", callback_data=f"buy_stars:{pl['id']}")]
        for pl in plans
    ]
    rows.append([InlineKeyboardButton(text=btn_webapp, web_app=WebAppInfo(url=f"{WEB_APP_URL}#profile"))])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(text=text, parse_mode="HTML", reply_markup=kb)
