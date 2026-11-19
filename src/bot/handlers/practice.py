"""
Learning Modes: Category Practice and Quick Test Handlers.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine
from src.bot.handlers.quiz import render_session_question
from src.bot.keyboards import get_categories_keyboard
from src.bot.config import QUICK_TEST_QUESTIONS
from src.bot.strings import get_str

practice_router = Router(name="practice_router")

# --- Quick Test ---
@practice_router.message(F.text.in_([
    "⏱️ Tezkor ekspress-test (10)",
    "⏱️ Тезкор экспресс-тест (10)",
    "⏱️ Экспресс-тест (10 вопросов)",
    "⚡ Tezkor test",
    "⚡ Тезкор тест",
    "⚡ Быстрый тест (10)"
]))
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
        text = "🚦 <b>ЙҲҚ МАВЗУЛАРИ БЎЙИЧА СИНОВ</b>\n\nКеракли бўлимни танланг:"
    elif lang == "ru":
        text = "🚦 <b>ТЕСТИРОВАНИЕ ПО ТЕМАМ ПДД</b>\n\nВыберите нужный раздел:"
    else:
        text = "🚦 <b>YHQ MAVZULARI BO‘YICHA SINOV</b>\n\nKerakli bo‘limni tanlang:"

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
        text = "🚦 <b>ЙҲҚ МАВЗУЛАРИ БЎЙИЧА СИНОВ</b>\n\nКеракли бўлимни танланг:"
    elif lang == "ru":
        text = "🚦 <b>ТЕСТИРОВАНИЕ ПО ТЕМАМ ПДД</b>\n\nВыберите нужный раздел:"
    else:
        text = "🚦 <b>YHQ MAVZULARI BO‘YICHA SINOV</b>\n\nKerakli bo‘limni tanlang:"
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
