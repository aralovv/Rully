"""
Comprehensive Automated Tests for RULLY Telegram Mini App & API.
Covers: Auth, HMAC signature, Theory Exam, Categories, Practical Curriculum,
Checklist, Scenarios, and Static SPA serving.
"""

import os
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.security import generate_dev_init_data, verify_telegram_init_data

client = TestClient(app)

# 1. Security & Cryptographic Verification Tests
def test_security_hmac_verification(monkeypatch):
    # Valid generation with active or test mock token
    mock_tok = "0000000000:TEST_MOCK_BOT_TOKEN_NOT_REAL"
    active_token = os.getenv("BOT_TOKEN") or mock_tok
    init_data = generate_dev_init_data(user_id=8809526955, bot_token=active_token)
    is_valid, user_data = verify_telegram_init_data(init_data)
    assert is_valid is True
    assert user_data is not None
    assert user_data["id"] == 8809526955
    assert user_data["username"] == "kurs_savdo"

    # Multi-token fallback with previous token
    prev_tok = "0000000001:TEST_PREVIOUS_ROTATION_TOKEN"
    monkeypatch.setenv("BOT_PREVIOUS_TOKENS", prev_tok)
    init_data_old = generate_dev_init_data(user_id=8809526955, bot_token=prev_tok)
    is_valid_old, user_data_old = verify_telegram_init_data(init_data_old)
    assert is_valid_old is True
    assert user_data_old["id"] == 8809526955

    # Hash wrapped in #tgWebAppData= as passed by Telegram client
    import urllib.parse
    wrapped_hash = f"#tgWebAppData={urllib.parse.quote(init_data)}&tgWebAppVersion=8.0"
    is_valid_wrap, user_data_wrap = verify_telegram_init_data(wrapped_hash)
    assert is_valid_wrap is True
    assert user_data_wrap["id"] == 8809526955

    # Tampered / corrupted data
    corrupted_data = init_data.replace("8809526955", "1234567890")
    is_valid_bad, _ = verify_telegram_init_data(corrupted_data)
    assert is_valid_bad is False

    # Empty / missing data
    assert verify_telegram_init_data("")[0] is False
    assert verify_telegram_init_data("some=gibberish")[0] is False

# 2. Health Check
def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "rully-miniapp-api"
    assert data["version"] == "2.1.0"

# 3. Authentication & User Profile
def test_auth_telegram_endpoint():
    init_data = generate_dev_init_data(user_id=8809526955)
    res = client.post("/api/auth/telegram", json={"init_data": init_data})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["user"]["user_id"] == 8809526955
    assert "streak" in data
    assert "stats" in data

def test_user_profile_and_language():
    # Fetch profile
    res = client.get("/api/user/me")
    assert res.status_code == 200
    data = res.json()
    assert "user" in data
    assert "streak" in data
    assert "stats" in data
    assert "history" in data

    # Update language to Russian
    res_lang = client.post("/api/user/language", json={"language": "ru"})
    assert res_lang.status_code == 200
    assert res_lang.json()["language"] == "ru"

    # Update back to Uzbek Latin
    res_lang2 = client.post("/api/user/language", json={"language": "uz_latn"})
    assert res_lang2.status_code == 200
    assert res_lang2.json()["language"] == "uz_latn"

# 4. Multilingual Categories
def test_categories_endpoints_multilingual():
    # Uzbek Latin
    res_latn = client.get("/api/categories?lang=uz_latn")
    assert res_latn.status_code == 200
    data_latn = res_latn.json()
    assert data_latn["count"] >= 40
    assert len(data_latn["categories"]) >= 40
    assert all("category_id" in c and "name" in c and "question_count" in c for c in data_latn["categories"])

    # Uzbek Cyrillic
    res_cyrl = client.get("/api/categories?lang=uz_cyrl")
    assert res_cyrl.status_code == 200
    data_cyrl = res_cyrl.json()
    assert data_cyrl["count"] == data_latn["count"]
    # Check that Cyrillic text does not equal Latin text
    assert data_cyrl["categories"][0]["name"] != data_latn["categories"][0]["name"]

    # Russian
    res_ru = client.get("/api/categories?lang=ru")
    assert res_ru.status_code == 200
    data_ru = res_ru.json()
    assert data_ru["count"] == data_latn["count"]

# 5. Question Detail
def test_question_detail_endpoint():
    res = client.get("/api/questions/CANON-YHQ-0001?lang=uz_latn")
    assert res.status_code == 200
    q = res.json()
    assert q["canonical_id"] == "CANON-YHQ-0001"
    assert len(q["options"]) >= 2
    assert "question_text" in q
    assert q["has_image"] is True
    assert q["image_url"] is not None
    assert q["image_url"].startswith("/images/")

# 6. Exam Session Lifecycle & Subscription Enforcement (Free Block -> Activate -> Start -> Answer -> Finish)
def test_exam_session_lifecycle():
    from src.bot.database import BotDatabase
    db = BotDatabase(os.getenv("DB_PATH", "master_database.sqlite"))
    # Reset dev user to free tier first
    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_pro = 0, subscription_tier = 'free', subscription_expires_at = NULL WHERE user_id = 8809526955")
        conn.execute("DELETE FROM exam_results WHERE user_id = 8809526955")
        conn.commit()

    # 1. New user with 0 exams can use free tier (Exam 1 & Exam 2)
    free_exam_1 = client.post("/api/session/start", json={
        "session_type": "EXAM",
        "total_questions": 20,
        "language": "uz_latn"
    })
    assert free_exam_1.status_code == 200
    sid_1 = free_exam_1.json()["session_id"]

    free_exam_2 = client.post("/api/session/start", json={
        "session_type": "EXAM",
        "total_questions": 20,
        "language": "uz_latn"
    })
    assert free_exam_2.status_code == 200
    sid_2 = free_exam_2.json()["session_id"]

    # Record 2 completed exams to exhaust free tier
    with db._get_connection() as conn:
        conn.execute("""
            INSERT INTO exam_results (session_id, user_id, total_questions, correct_count, incorrect_count, percentage, passed, time_taken_seconds, category_breakdown_json, created_at)
            VALUES (?, 8809526955, 20, 18, 2, 90.0, 1, 600, '{}', '2026-01-01T00:00:00'),
                   (?, 8809526955, 20, 19, 1, 95.0, 1, 550, '{}', '2026-01-01T01:00:00')
        """, (sid_1, sid_2))
        conn.commit()

    # 3rd exam attempt should be blocked (403 SUBSCRIPTION_REQUIRED)
    blocked_res = client.post("/api/session/start", json={
        "session_type": "EXAM",
        "total_questions": 20,
        "language": "uz_latn"
    })
    assert blocked_res.status_code == 403
    assert blocked_res.json()["detail"] == "SUBSCRIPTION_REQUIRED"

    # 2. Activate PRO subscription (14 days / 14 000 UZS)
    act_res = client.post("/api/subscription/activate", json={"plan_id": "pro_14"})
    assert act_res.status_code == 200
    sub_data = act_res.json()["subscription"]
    assert sub_data["is_pro"] is True
    assert sub_data["tier"] == "pro_14"
    assert sub_data["days_left"] >= 14

    # 3. PRO user starts EXAM successfully
    start_res = client.post("/api/session/start", json={
        "session_type": "EXAM",
        "total_questions": 20,
        "language": "uz_latn"
    })
    assert start_res.status_code == 200
    session_data = start_res.json()
    session_id = session_data["session_id"]
    assert session_id.startswith("SES-")
    assert session_data["total_questions"] == 20
    assert len(session_data["questions"]) == 20
    first_q = session_data["questions"][0]

    # Submit Answer
    ans_res = client.post("/api/session/answer", json={
        "session_id": session_id,
        "canonical_id": first_q["canonical_id"],
        "selected_key": "A",
        "language": "uz_latn"
    })
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert "is_correct" in ans_data
    assert "correct_key" in ans_data
    assert "explanation" in ans_data

    # Finish Session
    finish_res = client.post("/api/session/finish", json={
        "session_id": session_id,
        "time_elapsed_seconds": 120.5
    })
    assert finish_res.status_code == 200
    fin_data = finish_res.json()
    assert fin_data["session_id"] == session_id
    assert fin_data["total_questions"] == 20
    assert "percentage" in fin_data
    assert "passed" in fin_data
    assert "category_breakdown" in fin_data

# 7. Bookmarks and Mistakes
def test_bookmarks_and_mistakes():
    # Toggle bookmark
    bm_res = client.post("/api/bookmarks/toggle", json={"canonical_id": "CANON-YHQ-0001"})
    assert bm_res.status_code == 200
    is_bm = bm_res.json()["is_bookmarked"]

    # List bookmarks
    list_bm = client.get("/api/bookmarks?lang=uz_latn")
    assert list_bm.status_code == 200
    assert "questions" in list_bm.json()

    # Untoggle
    bm_res2 = client.post("/api/bookmarks/toggle", json={"canonical_id": "CANON-YHQ-0001"})
    assert bm_res2.status_code == 200
    assert bm_res2.json()["is_bookmarked"] == (not is_bm)

    # Mistakes pool
    mistakes_res = client.get("/api/mistakes?lang=uz_latn")
    assert mistakes_res.status_code == 200
    assert "questions" in mistakes_res.json()

# 8. Practical Driving Modules Curriculum
def test_practical_modules_curriculum():
    # List modules
    res = client.get("/api/amaliy/modules?lang=uz_latn")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 10
    assert len(data["modules"]) == 10
    assert "completed_count" in data
    assert "completion_percentage" in data

    # Module Detail
    mod_res = client.get("/api/amaliy/modules/MOD-01?lang=uz_latn")
    assert mod_res.status_code == 200
    mod = mod_res.json()
    assert mod["id"] == "MOD-01"
    assert len(mod["steps"]) >= 3
    assert len(mod["common_mistakes"]) >= 2
    assert "disqualification_trap" in mod
    assert len(mod["disqualification_trap"]) > 0
    assert "is_completed" in mod

    # Toggle Module Completion
    tog_mod = client.post("/api/amaliy/modules/toggle", json={"module_id": "MOD-01"})
    assert tog_mod.status_code == 200
    assert "is_completed" in tog_mod.json()

# 9. Deprecated Checklist & Scenarios endpoints cleanly removed (404)
def test_removed_practical_subfeatures_absent():
    assert client.get("/api/amaliy/checklist?lang=uz_latn").status_code == 404
    assert client.get("/api/amaliy/scenarios?lang=uz_latn").status_code == 404

# 12. Static Frontend Single Page Application
def test_static_frontend_files():
    # Root index.html
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "text/html" in root_res.headers.get("content-type", "")
    assert "RULLY" in root_res.text
    assert "telegram-web-app.js" in root_res.text

    # CSS
    css_res = client.get("/static/css/rully.css")
    assert css_res.status_code == 200
    assert "--color-primary" in css_res.text

    # Javascript
    app_js_res = client.get("/static/js/app.js")
    assert app_js_res.status_code == 200
    assert "initApp" in app_js_res.text

    trans_js_res = client.get("/static/js/translations.js")
    assert trans_js_res.status_code == 200
    assert "uz_latn" in trans_js_res.text
    assert "uz_cyrl" in trans_js_res.text
    assert "ru" in trans_js_res.text


# 13. Subscription System (Plans, Pricing & Activation)
def test_subscription_plans_and_flow():
    # 1. Check plans list and pricing
    plans_res = client.get("/api/subscription/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()["plans"]
    assert len(plans) == 2
    p14 = next(p for p in plans if p["id"] == "pro_14")
    p30 = next(p for p in plans if p["id"] == "pro_30")
    assert p14["duration_days"] == 14
    assert p14["price_uzs"] == 14000
    assert p30["duration_days"] == 30
    assert p30["price_uzs"] == 25000

    # 2. Check activate 30-day plan
    act_res = client.post("/api/subscription/activate", json={"plan_id": "pro_30"})
    assert act_res.status_code == 200
    sub = act_res.json()["subscription"]
    assert sub["is_pro"] is True
    assert sub["tier"] == "pro_30"
    assert sub["days_left"] >= 30

    # 3. Check status endpoint
    stat_res = client.get("/api/subscription/status")
    assert stat_res.status_code == 200
    assert stat_res.json()["subscription"]["is_pro"] is True

# 14. Custom Quiz Subscription Limits (Free: 10 & 20 allowed, 30+ locked)
def test_custom_quiz_subscription_limits():
    from src.bot.database import BotDatabase
    db = BotDatabase(os.getenv("DB_PATH", "master_database.sqlite"))
    # Reset dev user to free tier
    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_pro = 0, subscription_tier = 'free', subscription_expires_at = NULL WHERE user_id = 8809526955")
        conn.commit()

    # Free user can start CUSTOM quiz with 10 questions
    res_10 = client.post("/api/session/start", json={
        "session_type": "CUSTOM",
        "total_questions": 10,
        "language": "uz_latn"
    })
    assert res_10.status_code == 200
    assert res_10.json()["total_questions"] == 10

    # Free user can start CUSTOM quiz with 20 questions
    res_20 = client.post("/api/session/start", json={
        "session_type": "CUSTOM",
        "total_questions": 20,
        "language": "uz_latn"
    })
    assert res_20.status_code == 200
    assert res_20.json()["total_questions"] == 20

    # Free user CANNOT start CUSTOM quiz with 30 questions (403 SUBSCRIPTION_REQUIRED)
    res_30 = client.post("/api/session/start", json={
        "session_type": "CUSTOM",
        "total_questions": 30,
        "language": "uz_latn"
    })
    assert res_30.status_code == 403
    assert res_30.json()["detail"] == "SUBSCRIPTION_REQUIRED"

    # Free user CANNOT start CUSTOM quiz with 50 questions
    res_50 = client.post("/api/session/start", json={
        "session_type": "CUSTOM",
        "total_questions": 50,
        "language": "uz_latn"
    })
    assert res_50.status_code == 403

    # Activate PRO subscription
    act_res = client.post("/api/subscription/activate", json={"plan_id": "pro_14"})
    assert act_res.status_code == 200

    # PRO user CAN start CUSTOM quiz with 30 questions
    res_30_pro = client.post("/api/session/start", json={
        "session_type": "CUSTOM",
        "total_questions": 30,
        "language": "uz_latn"
    })
    assert res_30_pro.status_code == 200
    assert res_30_pro.json()["total_questions"] == 30

