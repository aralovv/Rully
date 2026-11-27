"""
RULLY 2.0 Architecture, Database, Analytics, Bilet Tickets & AI Tool Execution Tests.
All DB-mutating tests operate on an isolated temporary SQLite copy of master_database.sqlite.
"""

import os
import shutil
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.deps import get_db
from src.api.security import generate_dev_init_data
from src.avtotest_product import AvtotestProductEngine
from src.bot.database import BotDatabase
from src.database_migrations import run_migrations
from src.ai.gemini_service import GeminiService


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Creates a clean isolated SQLite database with all RULLY 2.0 migrations applied."""
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_copy = tmp_path / "rully2_unit.sqlite"
    shutil.copy2("master_database.sqlite", db_copy)
    run_migrations(str(db_copy))
    db = BotDatabase(str(db_copy))
    yield db


@pytest.fixture
def isolated_client(isolated_db):
    app.dependency_overrides[get_db] = lambda: isolated_db
    try:
        yield TestClient(app), isolated_db
    finally:
        app.dependency_overrides.clear()


def test_deterministic_67_tickets_cover_all_questions():
    engine = AvtotestProductEngine("master_database.sqlite")
    total_q = engine.get_total_question_count()
    assert total_q == 1327
    tickets = engine.get_tickets_summary("uz_latn")
    assert len(tickets) == 67

    seen_ids = set()
    for idx, t in enumerate(tickets, start=1):
        assert t["ticket_number"] == idx
        qids = engine.get_ticket_question_ids(idx)
        if idx < 67:
            assert len(qids) == 20
        else:
            assert len(qids) == 7
        seen_ids.update(qids)

    # Zero overlap, 100% coverage of all 1,327 canonical questions
    assert len(seen_ids) == total_q


def test_streak_consecutive_day_rollover_and_reset(isolated_db):
    from src.db.tz_utils import tashkent_now, tashkent_yesterday_str
    uid = 990001001
    isolated_db.get_or_create_user(uid, username="streak_tester")
    # Simulate active yesterday (Asia/Tashkent UTC+5) with streak = 4
    t_now = tashkent_now()
    yesterday = tashkent_yesterday_str(t_now)
    now_ts = datetime.utcnow().isoformat()
    with isolated_db._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
            VALUES (?, 4, ?, 20, 15, ?)
            """,
            (uid, yesterday, now_ts),
        )
        conn.commit()

    # Auth bundle before answering today must show today_questions_count == 0
    bundle = isolated_db.get_user_full_auth_bundle(uid)
    assert bundle["streak"]["current_streak"] == 4
    assert bundle["streak"]["today_questions_count"] == 0

    sess = isolated_db.create_session(uid, "CATEGORY", "uz_latn", ["CANON-YHQ-0001", "CANON-YHQ-0002"], category_id=1)
    res1 = isolated_db.process_session_answer(sess["session_id"], uid, "CANON-YHQ-0001", "A", "A", True, "CATEGORY")
    assert res1["streak"]["current_streak"] == 5
    assert res1["streak"]["today_questions_count"] == 1

    # Same-day second answer increments today count and preserves streak=5
    res2 = isolated_db.process_session_answer(sess["session_id"], uid, "CANON-YHQ-0002", "B", "B", True, "CATEGORY")
    assert res2["streak"]["current_streak"] == 5
    assert res2["streak"]["today_questions_count"] == 2

    # Missed 3 days resets streak back to 1
    old_day = (t_now - timedelta(days=3)).strftime("%Y-%m-%d")
    with isolated_db._get_connection() as conn:
        conn.execute("UPDATE learning_streak SET last_active_date = ?, today_questions_count = 12 WHERE user_id = ?", (old_day, uid))
        conn.commit()

    sess2 = isolated_db.create_session(uid, "CATEGORY", "uz_latn", ["CANON-YHQ-0003"], category_id=1)
    res3 = isolated_db.process_session_answer(sess2["session_id"], uid, "CANON-YHQ-0003", "A", "A", True, "CATEGORY")
    assert res3["streak"]["current_streak"] == 1
    assert res3["streak"]["today_questions_count"] == 1


def test_tickets_api_analytics_adaptive_and_review_lifecycle(isolated_client):
    client, db = isolated_client
    uid = 8809526955
    db.get_or_create_user(uid, username="qa_driver")
    with db._get_connection() as conn:
        conn.execute("DELETE FROM session_answers WHERE user_id = ? OR session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)", (uid, uid))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_ticket_progress WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_mistakes WHERE user_id = ?", (uid,))
        conn.commit()

    # 1. Custom daily goal
    goal_res = client.post("/api/user/daily-goal", json={"daily_goal": 30})
    assert goal_res.status_code == 200
    assert goal_res.json()["daily_goal_questions"] == 30

    # 2. List all 67 tickets
    t_res = client.get("/api/tickets?lang=uz_latn")
    assert t_res.status_code == 200
    t_data = t_res.json()
    assert t_data["total_tickets"] == 67
    assert t_data["tickets"][0]["ticket_number"] == 1
    assert t_data["tickets"][0]["question_count"] == 20
    assert t_data["tickets"][-1]["question_count"] == 7

    # 3. Start Ticket #67 (7 questions) & answer all 7 correctly
    start_bilet = client.post("/api/session/start", json={
        "session_type": "BILET",
        "ticket_number": 67,
        "language": "uz_latn"
    })
    assert start_bilet.status_code == 200
    s_data = start_bilet.json()
    assert s_data["total_questions"] == 7
    sid = s_data["session_id"]

    for q in s_data["questions"]:
        ans = client.post("/api/session/answer", json={
            "session_id": sid,
            "canonical_id": q["canonical_id"],
            "selected_key": q["correct_option_key"],
            "language": "uz_latn"
        })
        assert ans.status_code == 200
        assert ans.json()["is_correct"] is True

    fin = client.post("/api/session/finish", json={"session_id": sid, "time_elapsed_seconds": 42.0})
    assert fin.status_code == 200
    assert fin.json()["passed"] is True

    # Verify Ticket #67 shows as passed in GET /api/tickets
    t_after = client.get("/api/tickets?lang=uz_latn").json()
    assert t_after["passed_tickets"] == 1
    assert t_after["tickets"][-1]["is_passed"] is True
    assert t_after["tickets"][-1]["best_correct"] == 7

    # 4. Verify Post-Session Review Endpoint
    rev = client.get(f"/api/session/{sid}/review?lang=uz_latn")
    assert rev.status_code == 200
    rev_data = rev.json()
    assert len(rev_data["items"]) == 7
    assert rev_data["items"][0]["selected_key"] == rev_data["items"][0]["correct_option_key"]
    assert rev_data["items"][0]["is_correct"] is True

    # 5. IDOR protection on /review for session owned by another user
    other_uid = 777000111
    db.get_or_create_user(other_uid, username="other_user")
    other_sess = db.create_session(other_uid, "BILET", "uz_latn", ["CANON-YHQ-0001"], category_id=1)
    forbidden = client.get(f"/api/session/{other_sess['session_id']}/review")
    assert forbidden.status_code == 403

    # 6. Analytics & Adaptive recommendations
    ana = client.get("/api/learning/analytics?lang=uz_latn")
    assert ana.status_code == 200
    ana_data = ana.json()
    assert ana_data["unique_answered"] == 7
    assert ana_data["passed_tickets"] == 1
    assert "recommendation" in ana_data
    assert len(ana_data["milestones"]) >= 6

    # 7. Start ADAPTIVE practice session
    adap = client.post("/api/session/start", json={
        "session_type": "ADAPTIVE",
        "total_questions": 10,
        "language": "uz_latn"
    })
    assert adap.status_code == 200
    assert adap.json()["total_questions"] == 10


def test_health_header_and_timing_middleware(isolated_client):
    client, _ = isolated_client
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["version"] == "2.1.0"
    assert res.json()["platform_version"] == "2.0.0"
    assert "X-Process-Time-Ms" in res.headers


def test_ai_service_tool_execution_loop(isolated_db, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123456")
    uid = 8809526955
    isolated_db.get_or_create_user(uid, username="ai_tester")
    service = GeminiService()

    # Round 1 returns functionCall to get_user_statistics, Round 2 returns grounded text
    round1_resp = {
        "candidates": [{
            "content": {
                "parts": [{
                    "functionCall": {
                        "name": "get_user_statistics",
                        "args": {}
                    }
                }]
            }
        }]
    }
    round2_resp = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": "Sizning statistikangiz tekshirildi. Harakatni davom ettiring!"
                }]
            }
        }]
    }

    with patch("src.ai.gemini_service.get_db_connection", side_effect=isolated_db._get_connection):
        with patch.object(
            GeminiService,
            "_call_gemini_with_fallback",
            new=AsyncMock(side_effect=[(round1_resp, 200, None), (round2_resp, 200, None)])
        ):
            out = asyncio.run(service.chat(
                user_id=uid,
                session_id="test-ai-tools",
                message="Mening statistikam qanday?",
                is_pro=True,
                language="uz_latn",
                student_snapshot={"unique_answered": 12, "passed_exams": 1, "total_exams": 2, "active_mistakes": 3},
            ))
            assert out["ok"] is True
            assert "statistikangiz" in out["reply"].lower()
