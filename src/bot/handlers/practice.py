"""
Learning Modes: Category Practice and Quick Test Handlers.
"""
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine
from src.bot.handlers.quiz import render_session_question
from src.bot.keyboards import (
    get_categories_keyboard,
    get_bilet_selection_keyboard,
    get_deep_link_card_keyboard,
)
from src.bot.config import QUICK_TEST_QUESTIONS
from src.bot.strings import get_str

practice_router = Router(name="practice_router")

# --- Quick Test ---
@practice_router.message(F.text.in_(["⚡ Tezkor test", "⚡ Тезкор тест", "⚡ Быстрый тест (10)"]))
@practice_router.callback_query(F.data == "menu:quick")
async def start_quick_test(event: Message | CallbackQuery, bot: Bot,
                           product_engine: AvtotestProductEngine, db: BotDatabase):
    user_id = event.from_user.id
    chat_id = event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
    lang = db.get_user_language(user_id)

    if isinstance(event, CallbackQuery):
        await event.answer()

    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT canonical_id FROM canonical_questions ORDER BY RANDOM() LIMIT ?", (QUICK_TEST_QUESTIONS,))
        qids = [r["canonical_id"] for r in c.fetchall()]

    session = db.create_session(
        user_id=user_id,
        session_type="QUICK",
        language=lang,
        question_ids=qids,
        time_limit_seconds=0 # Untimed
    )

    await render_session_question(bot, chat_id, session, product_engine, db)

# --- Category Practice ---
@practice_router.callback_query(F.data == "menu:categories")
async def show_categories(callback: CallbackQuery, product_engine: AvtotestProductEngine, db: BotDatabase):
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()

    categories = product_engine.get_categories(language=lang)
    kb = get_categories_keyboard(categories, page=0, language=lang)

    if lang == "uz_cyrl":
        text = "🎯 <b>БОБ БЎЙИЧА МАШҚ</b>\n\nКеракли ЙҲҚ бўлимини танланг:"
    elif lang == "ru":
        text = "🎯 <b>ТРЕНИРОВКА ПО ТЕМАМ</b>\n\nВыберите нужный раздел ПДД:"
    else:
        text = "🎯 <b>BOB BO‘YICHA MASHQ</b>\n\nKerakli YHQ mavzusini tanlang:"

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=kb
    )

@practice_router.callback_query(F.data.startswith("cat:page:"))
async def paginate_categories(callback: CallbackQuery, product_engine: AvtotestProductEngine, db: BotDatabase):
    page = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()

    categories = product_engine.get_categories(language=lang)
    kb = get_categories_keyboard(categories, page=page, language=lang)

    if lang == "uz_cyrl":
        text = "🎯 <b>БОБ БЎЙИЧА МАШҚ</b>\n\nКеракли ЙҲҚ бўлимини танланг:"
    elif lang == "ru":
        text = "🎯 <b>ТРЕНИРОВКА ПО ТЕМАМ</b>\n\nВыберите нужный раздел ПДД:"
    else:
        text = "🎯 <b>BOB BO‘YICHA MASHQ</b>\n\nKerakli YHQ mavzusini tanlang:"

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=kb
    )

@practice_router.callback_query(F.data.startswith("cat:select:"))
async def select_category(callback: CallbackQuery, bot: Bot,
                          product_engine: AvtotestProductEngine, db: BotDatabase):
    cat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    lang = db.get_user_language(user_id)
    await callback.answer()

    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT canonical_id FROM canonical_questions WHERE category_id = ? ORDER BY canonical_id", (cat_id,))
        qids = [r["canonical_id"] for r in c.fetchall()]

    if not qids:
        await callback.message.answer(get_str("error_generic", lang))
        return

    session = db.create_session(
        user_id=user_id,
        session_type="CATEGORY",
        category_id=cat_id,
        language=lang,
        question_ids=qids,
        time_limit_seconds=0
    )

    await render_session_question(bot, chat_id, session, product_engine, db)

@practice_router.callback_query(F.data == "cat:noop")
async def cat_noop(callback: CallbackQuery):
    await callback.answer()


# --- SM-2 Aqlli Takrorlash (SRS) ---
@practice_router.message(Command("srs"))
@practice_router.message(Command("takrorlash"))
@practice_router.callback_query(F.data == "menu:srs")
async def start_srs_review_flow(
    event: Message | CallbackQuery,
    bot: Bot,
    product_engine: AvtotestProductEngine,
    db: BotDatabase,
):
    user_id = event.from_user.id
    chat_id = event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
    lang = db.get_user_language(user_id)

    if isinstance(event, CallbackQuery):
        await event.answer()

    srs_data = db.get_srs_queue_summary(user_id, limit=20)
    due_ids = list(srs_data.get("due_question_ids") or [])[:10]

    if not due_ids:
        empty_text = get_str("srs_empty_info", lang)
        kb = get_deep_link_card_keyboard(
            "srs",
            get_str("btn_rully_app", lang),
            lang,
            inline_callback="menu:quick",
            inline_btn_text=get_str("btn_quick_test", lang),
        )
        if isinstance(event, CallbackQuery):
            await event.message.answer(empty_text, parse_mode="HTML", reply_markup=kb)
        else:
            await event.answer(empty_text, parse_mode="HTML", reply_markup=kb)
        return

    session = db.create_session(
        user_id=user_id,
        session_type="SRS",
        language=lang,
        question_ids=due_ids,
        time_limit_seconds=0,
    )
    await render_session_question(bot, chat_id, session, product_engine, db)


# --- Official Bilets (Tickets 1..67) ---
async def _launch_ticket_session(
    bot: Bot,
    chat_id: int,
    user_id: int,
    ticket_no: int,
    lang: str,
    product_engine: AvtotestProductEngine,
    db: BotDatabase,
) -> bool:
    qids = product_engine.get_ticket_question_ids(ticket_no)
    if not qids:
        return False
    session = db.create_session(
        user_id=user_id,
        session_type="BILET",
        language=lang,
        question_ids=qids,
        time_limit_seconds=0,
        category_id=ticket_no,
    )
    await render_session_question(bot, chat_id, session, product_engine, db)
    return True


@practice_router.message(Command("bilet"))
async def cmd_bilet(
    message: Message,
    command: CommandObject,
    bot: Bot,
    product_engine: AvtotestProductEngine,
    db: BotDatabase,
):
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    raw_arg = (command.args or "").strip()

    if raw_arg.isdigit():
        ticket_no = int(raw_arg)
        ok = await _launch_ticket_session(bot, message.chat.id, user_id, ticket_no, lang, product_engine, db)
        if ok:
            return

    total_tickets = product_engine.get_ticket_count()
    kb = get_bilet_selection_keyboard(total_tickets=total_tickets, page=0, language=lang)
    await message.answer(
        f"{get_str('bilets_title', lang)}\n\n{get_str('bilets_desc', lang)}",
        parse_mode="HTML",
        reply_markup=kb,
    )


@practice_router.callback_query(F.data == "menu:bilets")
async def show_bilet_menu(callback: CallbackQuery, product_engine: AvtotestProductEngine, db: BotDatabase):
    lang = db.get_user_language(callback.from_user.id)
    await callback.answer()
    total_tickets = product_engine.get_ticket_count()
    kb = get_bilet_selection_keyboard(total_tickets=total_tickets, page=0, language=lang)
    text = f"{get_str('bilets_title', lang)}\n\n{get_str('bilets_desc', lang)}"
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text=text, parse_mode="HTML", reply_markup=kb)


@practice_router.callback_query(F.data.startswith("bilet:page:"))
async def paginate_bilets(callback: CallbackQuery, product_engine: AvtotestProductEngine, db: BotDatabase):
    page = int(callback.data.split(":")[2])
    lang = db.get_user_language(callback.from_user.id)
    await callback.answer()
    total_tickets = product_engine.get_ticket_count()
    kb = get_bilet_selection_keyboard(total_tickets=total_tickets, page=page, language=lang)
    await callback.message.edit_reply_markup(reply_markup=kb)


@practice_router.callback_query(F.data.startswith("bilet:start:"))
async def start_bilet_callback(
    callback: CallbackQuery,
    bot: Bot,
    product_engine: AvtotestProductEngine,
    db: BotDatabase,
):
    ticket_no = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    await callback.answer()
    ok = await _launch_ticket_session(bot, callback.message.chat.id, user_id, ticket_no, lang, product_engine, db)
    if not ok:
        await callback.message.answer(get_str("error_generic", lang), parse_mode="HTML")


@practice_router.callback_query(F.data == "bilet:noop")
async def bilet_noop(callback: CallbackQuery):
    await callback.answer()
