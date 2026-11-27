"""
Comprehensive Automated Test Suite for Avtotest Telegram Bot.
Covers 3-language completeness, database persistence, session recovery, timer logic,
duplicate answer protection, rich message rendering, widget sandboxing, and admin security.
"""

import pytest
import sqlite3
import time
import os
from src.bot.database import BotDatabase
from src.bot.strings import STRINGS, get_str
from src.bot.keyboards import (
    get_language_keyboard, get_main_menu_keyboard,
    get_quiz_options_keyboard, get_categories_keyboard
)
from src.bot.rich_messages import format_rich_question, format_rich_result, build_progress_bar
from src.bot.widgets import build_progress_widget_html, build_result_widget_html
from src.avtotest_product import AvtotestProductEngine
from src.bot.config import EXAM_TOTAL_QUESTIONS, EXAM_PASSING_SCORE, EXAM_TIME_LIMIT_SECONDS

DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")

@pytest.fixture(autouse=True, scope="module")
def cleanup_bot_test_users():
    def _clean():
        with sqlite3.connect(DB_PATH) as conn:
            real_ids = (1956239701, 8515329556, 8809526955)
            conn.execute("DELETE FROM session_answers WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id NOT IN (?, ?, ?))", real_ids)
            conn.execute("DELETE FROM session_answers WHERE session_id NOT IN (SELECT session_id FROM user_sessions)")
            conn.execute("DELETE FROM exam_results WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_mistakes WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_bookmarks WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_completed_modules WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM learning_streak WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM payment_transactions WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM payment_review_cases WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM payment_orders WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_sessions WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_subscriptions WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM user_activity_events WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.execute("DELETE FROM telegram_users WHERE user_id NOT IN (?, ?, ?)", real_ids)
            conn.commit()
    _clean()
    yield
    _clean()

@pytest.fixture(scope="module")
def bot_db():
    return BotDatabase(DB_PATH)

@pytest.fixture(scope="module")
def product_engine():
    return AvtotestProductEngine(DB_PATH)

# 1. Three-Language Localization Integrity
def test_all_languages_have_identical_keys():
    langs = ["uz_latn", "uz_cyrl", "ru"]
    base_keys = set(STRINGS["uz_latn"].keys())
    for l in langs:
        assert l in STRINGS, f"Language {l} missing in STRINGS"
        diff = base_keys - set(STRINGS[l].keys())
        assert not diff, f"Language {l} missing keys: {diff}"

def test_get_str_interpolation():
    msg = get_str("question_progress", "uz_latn", current=5, total=20)
    assert "5/20" in msg
    msg_ru = get_str("question_progress", "ru", current=1, total=20)
    assert "1/20" in msg_ru

# 2. User & Session Database Integrity
def test_user_registration_and_language_switching(bot_db):
    test_uid = 999001
    with bot_db._get_connection() as conn:
        conn.execute("DELETE FROM session_answers WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)", (test_uid,))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (test_uid,))
        conn.execute("DELETE FROM telegram_users WHERE user_id = ?", (test_uid,))
        conn.commit()
    user = bot_db.get_or_create_user(test_uid, "tester", "John", "Doe", default_lang="uz_latn")
    assert user["user_id"] == test_uid
    assert user["language"] == "uz_latn"

    # Switch language to Russian
    ok = bot_db.set_user_language(test_uid, "ru")
    assert ok is True
    assert bot_db.get_user_language(test_uid) == "ru"

    # Switch language to Uzbek Cyrillic
    bot_db.set_user_language(test_uid, "uz_cyrl")
    assert bot_db.get_user_language(test_uid) == "uz_cyrl"

def test_session_creation_and_recovery(bot_db):
    test_uid = 999002
    bot_db.get_or_create_user(test_uid, "tester2")
    qids = ["CANON-YHQ-0001", "CANON-YHQ-0002", "CANON-YHQ-0003"]
    session = bot_db.create_session(
        user_id=test_uid,
        session_type="EXAM",
        language="uz_latn",
        question_ids=qids,
        time_limit_seconds=1500
    )
    assert session["session_id"].startswith("SES-")
    assert session["status"] == "IN_PROGRESS"
    assert session["deadline"] > time.time()
    assert session["question_ids"] == qids

    # Test session recovery
    recovered = bot_db.get_active_session(test_uid)
    assert recovered is not None
    assert recovered["session_id"] == session["session_id"]
    assert recovered["current_index"] == 0

# 3. Double-Submission / Race Condition Protection
def test_atomic_answer_saving_prevents_duplicate_submission(bot_db):
    test_uid = 999003
    bot_db.get_or_create_user(test_uid, "tester3")
    qids = ["CANON-YHQ-0010", "CANON-YHQ-0011"]
    session = bot_db.create_session(test_uid, "EXAM", "uz_latn", qids, time_limit_seconds=1500)
    sid = session["session_id"]

    # First answer submission -> Success
    res1 = bot_db.save_answer(sid, "CANON-YHQ-0010", "A", "A", True)
    assert res1 is True

    # Second answer submission for SAME question -> Must return False!
    res2 = bot_db.save_answer(sid, "CANON-YHQ-0010", "B", "A", False)
    assert res2 is False, "Duplicate callback submission must be rejected atomically!"

# 4. Mistake Recording & Resolution
def test_user_mistakes_lifecycle(bot_db):
    test_uid = 999004
    bot_db.get_or_create_user(test_uid, "tester4")
    qid = "CANON-YHQ-0020"

    # Record mistake
    bot_db.record_mistake(test_uid, qid)
    mistakes = bot_db.get_user_mistakes(test_uid)
    assert qid in mistakes

    # Resolve mistake
    bot_db.resolve_mistake(test_uid, qid)
    updated_mistakes = bot_db.get_user_mistakes(test_uid)
    assert qid not in updated_mistakes

# 5. Exam Results & Passing Criteria
def test_exam_result_evaluation_and_persistence(bot_db):
    test_uid = 999005
    bot_db.get_or_create_user(test_uid, "tester5")
    sid = f"SES-TEST-{test_uid}"
    
    # Create session first to satisfy FK
    bot_db.create_session(test_uid, "EXAM", "uz_latn", ["CANON-YHQ-0001"] * 20, 1500)
    with bot_db._get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO user_sessions (session_id, user_id, session_type, language, total_questions, start_time, question_ids_json, created_at, updated_at) VALUES (?, ?, 'EXAM', 'uz_latn', 20, 0, '[]', '', '')", (sid, test_uid))
        conn.commit()

    # 18 correct out of 20 = Passed
    bot_db.save_exam_result(
        session_id=sid, user_id=test_uid, total_q=20,
        correct=18, incorrect=2, pct=90.0, passed=True,
        time_spent=600.0, category_breakdown={"Umumiy": {"correct": 18, "total": 20}}
    )
    
    history = bot_db.get_user_exam_history(test_uid)
    assert len(history) >= 1
    assert history[0]["passed"] == 1
    assert history[0]["percentage"] == 90.0

    stats = bot_db.get_user_stats(test_uid)
    assert stats["total_exams"] >= 1
    assert stats["passed_exams"] >= 1

# 6. Keyboards & Navigation
def test_language_keyboard_structure():
    kb = get_language_keyboard()
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "lang:uz_latn" in callbacks
    assert "lang:uz_cyrl" in callbacks
    assert "lang:ru" in callbacks

def test_main_menu_keyboard_structure():
    from src.bot.config import WEB_APP_URL
    for lang in ["uz_latn", "uz_cyrl", "ru"]:
        kb = get_main_menu_keyboard(lang)
        all_buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(all_buttons) == 2

        # 1. Direct RULLY app launcher button
        assert any(btn.web_app and WEB_APP_URL in btn.web_app.url for btn in all_buttons)
        # 2. Help callback button
        assert any(btn.callback_data == "menu:help" for btn in all_buttons)

def test_one_time_language_selection_flag(bot_db):
    test_uid = 999099
    with bot_db._get_connection() as conn:
        conn.execute("DELETE FROM session_answers WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)", (test_uid,))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (test_uid,))
        conn.execute("DELETE FROM telegram_users WHERE user_id = ?", (test_uid,))
        conn.commit()

    # Brand new user -> has_user_selected_language must be False
    user = bot_db.get_or_create_user(test_uid, "new_user")
    assert bot_db.has_user_selected_language(test_uid) is False

    # User explicitly selects language
    bot_db.set_user_language(test_uid, "uz_cyrl")
    assert bot_db.has_user_selected_language(test_uid) is True
    assert bot_db.get_user_language(test_uid) == "uz_cyrl"

def test_quiz_options_keyboard_callbacks():
    options = [{"key": "A", "text": "Opt A"}, {"key": "B", "text": "Opt B"}]
    kb = get_quiz_options_keyboard(options, session_id="SES-123", language="uz_latn")
    btns = [btn for row in kb.inline_keyboard for btn in row]
    assert any(b.callback_data == "ans:SES-123:A" for b in btns)
    assert any(b.callback_data == "ans:SES-123:B" for b in btns)
    assert any(b.callback_data == "quiz:finish:SES-123" for b in btns)

# 7. Rich Messages & Expandable Blockquotes
def test_rich_question_formatting_with_expandable_blockquote():
    options = [{"key": "A", "text": "Option 1"}, {"key": "B", "text": "Option 2"}]
    feedback = {
        "selected_key": "A",
        "correct_key": "A",
        "is_correct": True,
        "legal_reference": "YHQ 78-band",
        "explanation": "Shahar ichida 60 km/soat"
    }
    html_text = format_rich_question(
        session_type="EXAM",
        current_index=1,
        total_questions=20,
        category_name="Tezlik",
        question_text="Maksimal tezlik qancha?",
        options=options,
        language="uz_latn",
        feedback=feedback
    )
    assert "<blockquote expandable>" in html_text
    assert "</blockquote>" in html_text
    assert "YHQ 78-band" in html_text
    assert "Maksimal tezlik qancha?" in html_text

def test_rich_result_formatting():
    res_html = format_rich_result(
        total=20, correct=19, incorrect=1, time_spent_seconds=640,
        passed=True, category_breakdown={"Umumiy": {"correct": 19, "total": 20}},
        language="uz_latn"
    )
    assert "TABRIKLAYMIZ" in res_html
    assert "19 ta" in res_html
    assert "95.0%" in res_html
    assert "O‘TDI" in res_html

# 8. Widget HTML Sandboxing & Size Limits
def test_widget_html_sandboxing_and_size():
    prog_html = build_progress_widget_html(current=10, total=20, correct=8, incorrect=2)
    assert len(prog_html.encode('utf-8')) < 15000, "Progress widget must be <15KB"
    assert "<script" not in prog_html.lower(), "Widget must not contain scripts"
    assert "http://" not in prog_html and "https://" not in prog_html, "Widget must not make external calls"

    res_html = build_result_widget_html(total=20, correct=18, incorrect=2, passed=True, percentage=90.0)
    assert len(res_html.encode('utf-8')) < 15000, "Result widget must be <15KB"
    assert "IMTIHONDAN O'TDI" in res_html

# 9. Admin Authorization Security
def test_admin_stats_and_audit_logging(bot_db):
    stats = bot_db.get_admin_stats()
    assert stats["status"] == "HEALTHY"
    assert stats["canonical_questions"] >= 1295
    assert stats["canonical_translations"] >= 3885

    # Log action
    bot_db.log_admin_action(admin_id=5875526565, action="TEST_ACTION", details="Unit test verification")
    with bot_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT action FROM admin_audit_logs WHERE action = 'TEST_ACTION'")
        assert c.fetchone() is not None

# 10. Category Localization Purity Test
def test_category_localization_purity(product_engine):
    from src.bot.category_localization import CATEGORY_TRANSLATIONS, localize_category
    cats_latn = product_engine.get_categories(language="uz_latn")
    cats_cyrl = product_engine.get_categories(language="uz_cyrl")
    cats_ru = product_engine.get_categories(language="ru")

    assert len(cats_latn) == len(cats_cyrl) == len(cats_ru) >= 40

    import re
    for cat in cats_cyrl:
        # Check no Latin letters in Cyrillic categories
        assert not re.search(r'[A-Za-z]', cat["name"]), f"Latin detected in Cyrillic category: {cat['name']}"

    for cat in cats_ru:
        # Check no Latin letters in Russian categories
        assert not re.search(r'[A-Za-z]', cat["name"]), f"Latin detected in Russian category: {cat['name']}"

# 11. Legal Reference Sanitization & Localization Test
def test_legal_reference_localization_and_sanitization():
    from src.bot.category_localization import localize_legal_reference
    # Test Scope
    assert localize_legal_reference("General YHQ Scope", "uz_cyrl") == "ЙҲҚ умумий талаблари"
    assert localize_legal_reference("General YHQ Scope", "ru") == "Общие требования ПДД"

    # Test Annexes
    assert "ЙҲҚ 1-иловаси" in localize_legal_reference("Annex 1", "uz_cyrl")
    assert "Приложение 1 к ПДД" in localize_legal_reference("Annex 1", "ru")

    # Test Signs
    assert "3.27-йўл белгиси / чизиғи" in localize_legal_reference("3.27-yo'l belgisi / chizig'i", "uz_cyrl")
    assert "Дорожный знак / разметка 3.27" in localize_legal_reference("3.27-yo'l belgisi / chizig'i", "ru")

    # Test Raw english artifacts elimination
    sanitized = localize_legal_reference("Resolution 172, Chapter 16, Clause 104", "uz_cyrl")
    assert "Resolution" not in sanitized
    assert "Chapter" not in sanitized
    assert "Clause" not in sanitized

# 12. Custom Settings Widget Card Test
def test_custom_settings_widget_card():
    from src.bot.handlers.custom_test import format_settings_widget_card
    from src.bot.keyboards import get_custom_settings_keyboard

    settings = {"count": 30, "time_min": 10, "show_answer": True, "show_expl": False}
    card_text = format_settings_widget_card(settings, "uz_latn")
    assert "30 ta" in card_text
    assert "10 daqiqa" in card_text
    assert "TEST SOZLAMALARI" in card_text

    kb = get_custom_settings_keyboard(settings, "uz_latn")
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert any("🔘 30" in b.text for b in buttons)
    assert any("🔘 10m" in b.text for b in buttons)
    assert any(b.callback_data == "cfg:action:start" for b in buttons)

# 13. Card Widget Formatting Structure Test
def test_card_widget_formatting_structure():
    options = [
        {"key": "A", "text": "Variant A"},
        {"key": "B", "text": "Variant B"}
    ]
    card_html = format_rich_question(
        session_type="CUSTOM",
        current_index=1,
        total_questions=20,
        category_name="Umumiy qoidalar",
        question_text="Sinov savoli?",
        options=options,
        language="uz_cyrl",
        time_remaining_seconds=1200
    )
    # Check visual card container box
    assert "╭─" in card_html
    assert "╰─" in card_html
    assert "Ҳаракатланиш" in card_html or "Умумий қоидалар" in card_html
    assert "01 / 20" in card_html
    assert "20:00" in card_html

