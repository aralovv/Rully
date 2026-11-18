"""
Core Native Telegram Quiz Engine: Question Presentation, Instant Feedback,
Expandable Explanations, Race Condition Protection, and Session Completion.
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine
from src.bot.rich_messages import format_rich_question, format_rich_result
from src.bot.keyboards import get_quiz_options_keyboard, get_quiz_feedback_keyboard, get_results_keyboard
from src.bot.strings import get_str
from src.bot.widgets import build_result_widget_html, send_native_widget_or_fallback

logger = logging.getLogger(__name__)
quiz_router = Router(name="quiz_router")

async def render_session_question(bot: Bot, chat_id: int, session: Dict[str, Any],
                                  product_engine: AvtotestProductEngine, db: BotDatabase):
    """
    Renders the active question in the session.
    Automatically checks backend timer for timed exams.
    """
    session_id = session["session_id"]
    current_idx = session["current_index"]
    total_q = session["total_questions"]
    lang = session["language"]

    # 1. Check timer expiration
    if session.get("deadline") and time.time() > session["deadline"]:
        await bot.send_message(chat_id=chat_id, text=get_str("session_expired", lang), parse_mode="HTML")
        db.finish_session(session_id, status="EXPIRED")
        await render_session_results(bot, chat_id, session_id, product_engine, db)
        return

    # 2. Check completion
    if current_idx >= total_q:
        db.finish_session(session_id, status="COMPLETED")
        await render_session_results(bot, chat_id, session_id, product_engine, db)
        return

    # 3. Retrieve question
    canonical_id = session["question_ids"][current_idx]
    q_item = product_engine.get_question(canonical_id, language=lang, include_answer_key=True)
    if not q_item:
        logger.error(f"Question {canonical_id} not found in database")
        return

    # Calculate remaining time if exam
    time_remaining = None
    if session.get("deadline"):
        time_remaining = max(0, int(session["deadline"] - time.time()))

    # Build options list
    options_list = [{"key": opt.option_key, "text": opt.text} for opt in q_item.options]

    text = format_rich_question(
        session_type=session["session_type"],
        current_index=current_idx + 1,
        total_questions=total_q,
        category_name=q_item.category_name,
        question_text=q_item.question_text,
        options=options_list,
        language=lang,
        time_remaining_seconds=time_remaining,
        show_explanation=session.get("show_explanation", True)
    )

    reply_markup = get_quiz_options_keyboard(options_list, session_id=session_id, language=lang)

    # If question has an image, send as photo (from disk if available, or jsDelivr CDN if serverless)
    if q_item.has_image and q_item.image_path:
        if os.path.exists(q_item.image_path):
            photo_file = FSInputFile(q_item.image_path)
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_file,
                caption=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            filename = os.path.basename(q_item.image_path.replace("\\", "/"))
            cdn_base = os.getenv("IMAGE_CDN_BASE_URL", "https://cdn.jsdelivr.net/gh/aralovv/Rully@main/data/images/original").rstrip("/")
            cdn_url = f"{cdn_base}/{filename}"
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=cdn_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.warning(f"Could not send photo via CDN {cdn_url}: {e}, falling back to text")
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )


@quiz_router.callback_query(F.data.startswith("ans:"))
async def cb_submit_answer(callback: CallbackQuery, bot: Bot,
                          product_engine: AvtotestProductEngine, db: BotDatabase):
    """
    Handles user clicking on an option button (A, B, C, D).
    Guarantees idempotency via unique constraints and provides immediate feedback.
    """
    parts = callback.data.split(":")
    session_id = parts[1]
    selected_key = parts[2].upper()

    session = db.get_session(session_id)
    if not session or session["status"] != "IN_PROGRESS":
        await callback.answer(get_str("error_generic", "uz_latn"), show_alert=True)
        return

    lang = session["language"]
    user_id = callback.from_user.id
    current_idx = session["current_index"]

    # Check timer expiration
    if session.get("deadline") and time.time() > session["deadline"]:
        await callback.answer(get_str("session_expired", lang), show_alert=True)
        db.finish_session(session_id, status="EXPIRED")
        await render_session_results(bot, callback.message.chat.id, session_id, product_engine, db)
        return

    canonical_id = session["question_ids"][current_idx]
    q_item = product_engine.get_question(canonical_id, language=lang, include_answer_key=True)
    if not q_item:
        await callback.answer()
        return

    correct_key = q_item.correct_option_key
    is_correct = (selected_key == correct_key)

    # 1. Save answer atomically (returns False if already answered)
    saved = db.save_answer(session_id, canonical_id, selected_key, correct_key, is_correct)
    if not saved:
        await callback.answer(get_str("already_answered", lang), show_alert=False)
        return

    await callback.answer()

    # 2. Mistake tracking
    if not is_correct:
        db.record_mistake(user_id, canonical_id)
    else:
        if session["session_type"] == "MISTAKES":
            db.resolve_mistake(user_id, canonical_id)

    # Check auto-termination on 3rd mistake in EXAM mode (Uzbekistan DYHXX VMQ 408: max 2 mistakes)
    if session["session_type"] == "EXAM":
        answers = db.get_session_answers(session_id)
        mistakes_count = sum(1 for a in answers.values() if not a.get("is_correct"))
        if mistakes_count > 2:
            db.finish_session(session_id, status="FAILED_MISTAKES")
            alert_msg = {
                "uz_latn": "❌ Imtihon to‘xtatildi!\n2 tadan ortiq (3 ta) xatoga yo‘l qo‘yildi (DYHXX VMQ 408 qoidasi).",
                "uz_cyrl": "❌ Имтиҳон тўхтатилди!\n2 тадан ортиқ (3 та) хатога йўл қўйилди (ДЙҲХХ ВМҚ 408 қоидаси).",
                "ru": "❌ Экзамен остановлен!\nДопущено более 2 ошибок (правило ГСБДД ПКМ №408)."
            }.get(lang, "❌ Imtihon to‘xtatildi! 2 tadan ortiq xatoga yo‘l qo‘yildi.")
            await callback.answer(alert_msg, show_alert=True)
            await render_session_results(bot, callback.message.chat.id, session_id, product_engine, db)
            return

    # 3. Check whether immediate feedback is enabled for this test mode
    if not session.get("show_answer", True):
        # For official exam or custom test without instant answers: advance immediately
        new_index = db.advance_session(session_id)
        session["current_index"] = new_index
        await render_session_question(bot, callback.message.chat.id, session, product_engine, db)
        return

    # 4. Format feedback with expandable blockquote
    feedback = {
        "selected_key": selected_key,
        "correct_key": correct_key,
        "is_correct": is_correct,
        "legal_reference": q_item.legal_reference,
        "explanation": q_item.explanation
    }

    options_list = [{"key": opt.option_key, "text": opt.text} for opt in q_item.options]
    is_last = (current_idx + 1 >= session["total_questions"])

    time_remaining = None
    if session.get("deadline"):
        time_remaining = max(0, int(session["deadline"] - time.time()))

    feedback_text = format_rich_question(
        session_type=session["session_type"],
        current_index=current_idx + 1,
        total_questions=session["total_questions"],
        category_name=q_item.category_name,
        question_text=q_item.question_text,
        options=options_list,
        language=lang,
        time_remaining_seconds=time_remaining,
        feedback=feedback,
        show_explanation=session.get("show_explanation", True)
    )

    feedback_kb = get_quiz_feedback_keyboard(session_id=session_id, is_last_question=is_last, language=lang)

    # Edit caption if photo or text if regular message
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=feedback_text,
                parse_mode="HTML",
                reply_markup=feedback_kb
            )
        else:
            await callback.message.edit_text(
                text=feedback_text,
                parse_mode="HTML",
                reply_markup=feedback_kb
            )
    except Exception as e:
        logger.debug(f"Message edit error: {e}")


@quiz_router.callback_query(F.data.startswith("quiz:next:"))
async def cb_next_question(callback: CallbackQuery, bot: Bot,
                          product_engine: AvtotestProductEngine, db: BotDatabase):
    """
    Advances to next question or shows results if final question.
    """
    session_id = callback.data.split(":")[2]
    session = db.get_session(session_id)
    if not session:
        await callback.answer()
        return

    await callback.answer()
    chat_id = callback.message.chat.id

    # Advance current index
    new_index = db.advance_session(session_id)
    session["current_index"] = new_index

    # Render next question
    await render_session_question(bot, chat_id, session, product_engine, db)


@quiz_router.callback_query(F.data.startswith("quiz:finish:"))
async def cb_finish_early(callback: CallbackQuery, bot: Bot,
                         product_engine: AvtotestProductEngine, db: BotDatabase):
    """
    Prematurely finishes session and displays score.
    """
    session_id = callback.data.split(":")[2]
    await callback.answer()
    db.finish_session(session_id, status="COMPLETED")
    await render_session_results(bot, callback.message.chat.id, session_id, product_engine, db)


@quiz_router.callback_query(F.data == "quiz:noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


async def render_session_results(bot: Bot, chat_id: int, session_id: str,
                                 product_engine: AvtotestProductEngine, db: BotDatabase):
    """
    Calculates final exam / test score and displays rich score card.
    Saves to exam_results if session was an EXAM.
    """
    session = db.get_session(session_id)
    if not session:
        return

    lang = session["language"]
    total = session["total_questions"]
    correct = session["correct_count"]
    incorrect = session["incorrect_count"]
    time_spent = time.time() - session["start_time"]
    
    # Official standard (DYHXX VMQ 408): 18 correct answers to pass and at most 2 mistakes
    passed = (correct >= 18 and incorrect <= 2) if session["session_type"] == "EXAM" else (correct >= int(total * 0.8))
    pct = round((correct / total * 100), 1) if total > 0 else 0.0

    # Build category breakdown
    category_breakdown = {}
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
        SELECT cq.category_name, sa.is_correct
        FROM session_answers sa
        JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
        WHERE sa.session_id = ?
        """, (session_id,))
        for cat_name, is_c in c.fetchall():
            if cat_name not in category_breakdown:
                category_breakdown[cat_name] = {"correct": 0, "incorrect": 0, "total": 0}
            category_breakdown[cat_name]["total"] += 1
            if is_c:
                category_breakdown[cat_name]["correct"] += 1
            else:
                category_breakdown[cat_name]["incorrect"] += 1

    unanswered = max(0, total - (correct + incorrect))

    # Save exam result if it was an exam
    if session["session_type"] == "EXAM":
        db.save_exam_result(
            session_id=session_id,
            user_id=session["user_id"],
            total_q=total,
            correct=correct,
            incorrect=incorrect,
            pct=pct,
            passed=passed,
            time_spent=time_spent,
            category_breakdown=category_breakdown,
            unanswered=unanswered
        )

    # Format Rich Result Message
    result_text = format_rich_result(
        total=total,
        correct=correct,
        incorrect=incorrect,
        time_spent_seconds=time_spent,
        passed=passed,
        category_breakdown=category_breakdown,
        language=lang,
        unanswered=unanswered
    )

    has_mistakes = (incorrect > 0)
    reply_markup = get_results_keyboard(session_id=session_id, language=lang, has_mistakes=has_mistakes)

    # Build widget payload for Bot API 10.4 sendWidget capability
    widget_html = build_result_widget_html(total=total, correct=correct, incorrect=incorrect, passed=passed, percentage=pct)

    await send_native_widget_or_fallback(
        bot=bot,
        chat_id=chat_id,
        widget_html=widget_html,
        fallback_text=result_text,
        reply_markup=reply_markup
    )
