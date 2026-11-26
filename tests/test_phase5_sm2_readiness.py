"""
Phase 5 Verification Suite — SM-2 Spaced Repetition Engine, Migration 003 Parity,
Bayesian Readiness Integration, Daily "Aqlli Takrorlash" API & 3-Language UI Parity.

All mutating DB tests operate strictly on isolated temporary SQLite copies in tmp_path.
"""
import re
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.main import app
from src.bot.database import BotDatabase, compute_driver_accuracy, compute_driver_readiness
from src.database_migrations import run_migrations
from src.db.migrations_v2 import (
    apply_all_migrations,
    apply_phase5_migrations,
    rollback_phase5_migrations_local_test,
    verify_phase5_schema_parity,
)
from src.db.sanitized_export import WIPED_TABLES, export_sanitized_dev_sqlite
from src.db.sm2_engine import (
    SM2_MAX_EASE_FACTOR,
    SM2_MAX_INTERVAL_DAYS,
    SM2_MIN_EASE_FACTOR,
    classify_srs_mastery,
    compute_next_sm2_state,
    derive_sm2_quality,
)
from src.db.sqlite_utils import backup_sqlite_wal_safe, list_user_tables

ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    BotDatabase._ticket_schema_ready = False
    db_copy = tmp_path / "phase5_unit.sqlite"
    shutil.copy2("master_database.sqlite", db_copy)
    run_migrations(str(db_copy))
    yield BotDatabase(str(db_copy))


@pytest.fixture
def isolated_client(isolated_db):
    app.dependency_overrides[get_db] = lambda: isolated_db
    try:
        yield TestClient(app), isolated_db
    finally:
        app.dependency_overrides.clear()


def test_sm2_algorithm_transitions_bounds_and_lapses():
    t0 = datetime(2026, 11, 27, 10, 0, 0)

    # Quality derivation covers explicit, fast fluent, hesitant/mistake retry, and wrong answers
    assert derive_sm2_quality(True, explicit_quality=9) == 5
    assert derive_sm2_quality(False, explicit_quality=-2) == 0
    assert derive_sm2_quality(False, response_time_ms=1200) == 1
    assert derive_sm2_quality(False, previous_lapses=2, response_time_ms=9000) == 1
    assert derive_sm2_quality(False, response_time_ms=6500) == 2
    assert derive_sm2_quality(True, session_type="MISTAKES") == 3
    assert derive_sm2_quality(True, response_time_ms=25000) == 3
    assert derive_sm2_quality(True, session_type="SRS", response_time_ms=3200) == 5
    assert derive_sm2_quality(True, session_type="CATEGORY", response_time_ms=9500) == 4

    # Repetition 1 -> 1d; Rep 2 -> 6d; Rep 3 -> round(6 * EF); >= 21d -> MASTERED
    s1 = compute_next_sm2_state(None, quality=5, now=t0)
    assert s1["repetitions"] == 1
    assert s1["interval_days"] == 1
    assert s1["ease_factor"] == 2.6
    assert s1["mastery_level"] == "REVIEWING"

    s2 = compute_next_sm2_state(s1, quality=5, now=t0 + timedelta(days=1))
    assert s2["repetitions"] == 2
    assert s2["interval_days"] == 6
    assert s2["ease_factor"] == 2.7

    s3 = compute_next_sm2_state(s2, quality=5, now=t0 + timedelta(days=7))
    assert s3["repetitions"] == 3
    assert s3["interval_days"] == round(6 * 2.8)
    assert s3["interval_days"] < 21
    assert s3["mastery_level"] == "REVIEWING"

    s4 = compute_next_sm2_state(s3, quality=5, now=t0 + timedelta(days=24))
    assert s4["repetitions"] == 4
    assert s4["interval_days"] >= 21
    assert s4["mastery_level"] == "MASTERED"

    # Interval caps at 180 days & EF caps at 3.0
    huge = compute_next_sm2_state({"ease_factor": 2.98, "interval_days": 150, "repetitions": 6, "lapses": 0}, quality=5, now=t0)
    assert huge["interval_days"] == SM2_MAX_INTERVAL_DAYS
    assert huge["ease_factor"] <= SM2_MAX_EASE_FACTOR

    # Wrong answer (q < 3) resets reps, sets due immediately, increments lapses, and floors EF >= 1.3
    lapsed = compute_next_sm2_state(s4, quality=1, now=t0)
    assert lapsed["repetitions"] == 0
    assert lapsed["lapses"] == 1
    assert lapsed["interval_days"] == 0
    assert lapsed["is_due"] is True
    assert lapsed["mastery_level"] == "LEARNING"

    low_ef_state = {"ease_factor": 1.31, "interval_days": 1, "repetitions": 1, "lapses": 3}
    floored = compute_next_sm2_state(low_ef_state, quality=0, now=t0)
    assert floored["ease_factor"] == SM2_MIN_EASE_FACTOR
    assert classify_srs_mastery(1, 1, 2.5, lapses=2) == "LEARNING"


def test_migration_003_idempotency_rollback_and_sanitized_export(tmp_path):
    sim_db = str(tmp_path / "phase5_mig_sim.sqlite")
    backup_sqlite_wal_safe("master_database.sqlite", sim_db, allow_overwrite=True)

    conn = sqlite3.connect(sim_db)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Simulate pre-Phase-5 DB without user_question_srs
    conn.execute("DROP TABLE IF EXISTS user_question_srs;")
    conn.execute("DELETE FROM schema_migrations WHERE version = '003_phase5_user_question_srs';") if "schema_migrations" in list_user_tables(conn) else None
    conn.commit()

    # Apply Phase 5 twice -> completely idempotent & FK/parity valid
    res1 = apply_all_migrations(conn)
    res2 = apply_phase5_migrations(conn)
    assert res1["parity"]["passed"] is True
    assert res2["parity"]["passed"] is True
    assert verify_phase5_schema_parity(conn)["passed"] is True
    assert "user_question_srs" in set(list_user_tables(conn))
    assert conn.execute("PRAGMA integrity_check;").fetchone() == ("ok",)
    assert conn.execute("PRAGMA foreign_key_check;").fetchall() == []

    # Rollback drill removes Phase 5 cleanly without breaking existing tables
    rb = rollback_phase5_migrations_local_test(conn)
    assert rb["rolled_back"] is True
    assert "user_question_srs" not in set(list_user_tables(conn))
    apply_phase5_migrations(conn)

    # Seed user SRS data & confirm sanitized downward export wipes user_question_srs
    assert "user_question_srs" in WIPED_TABLES
    now_ts = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO telegram_users (user_id, username, language, created_at, last_active_at) VALUES (995511, 'srs_u', 'uz_latn', ?, ?)",
        (now_ts, now_ts),
    )
    conn.execute(
        """
        INSERT INTO user_question_srs (user_id, canonical_id, ease_factor, interval_days, repetitions, lapses, last_quality, last_reviewed_at, next_review_at)
        VALUES (995511, 'CANON-YHQ-0001', 2.6, 6, 2, 0, 5, ?, ?)
        """,
        (now_ts, now_ts),
    )
    conn.commit()

    sanitized_out = str(tmp_path / "sanitized_p5.sqlite")
    exp_res = export_sanitized_dev_sqlite(conn, sanitized_out)
    conn.close()
    assert exp_res["integrity_check"] == "ok"
    assert exp_res["foreign_key_check"] == "ok"

    dconn = sqlite3.connect(sanitized_out)
    assert "user_question_srs" in set(list_user_tables(dconn))
    assert dconn.execute("SELECT COUNT(*) FROM user_question_srs").fetchone()[0] == 0
    dconn.close()


def test_bayesian_accuracy_and_sm2_readiness_integration():
    # Neutral baseline when srs_tracked == 0 preserves backward compatibility
    base_acc = compute_driver_accuracy(
        total_answered=100,
        correct_answers=85,
        unique_questions=90,
        unique_correct=80,
        recent_total=40,
        recent_correct=36,
        categories_tested=10,
        unresolved_mistakes=2,
        return_details=True,
    )
    assert "bayesian_accuracy" in base_acc
    assert base_acc["srs_retention_rate"] == 100.0

    # High SM-2 mastery lifts retention-adjusted accuracy cleanly vs large overdue backlog
    mastered_acc = compute_driver_accuracy(
        total_answered=100, correct_answers=85, unique_questions=90, unique_correct=80,
        recent_total=40, recent_correct=36, categories_tested=10, unresolved_mistakes=2,
        srs_mastered=30, srs_due=0, srs_tracked=40,
    )
    overdue_acc = compute_driver_accuracy(
        total_answered=100, correct_answers=85, unique_questions=90, unique_correct=80,
        recent_total=40, recent_correct=36, categories_tested=10, unresolved_mistakes=2,
        srs_mastered=2, srs_due=25, srs_tracked=40,
    )
    assert mastered_acc > base_acc["accuracy"] > overdue_acc

    r_good = compute_driver_readiness(
        total_exams=4, passed_exams=3, pass_rate=75.0, total_answered=120,
        accuracy=86.0, unique_questions=100, unresolved_mistakes=2,
        srs_mastered=20, srs_due=1, srs_tracked=25, return_details=True,
    )
    r_due = compute_driver_readiness(
        total_exams=4, passed_exams=3, pass_rate=75.0, total_answered=120,
        accuracy=86.0, unique_questions=100, unresolved_mistakes=2,
        srs_mastered=1, srs_due=20, srs_tracked=25, return_details=True,
    )
    assert r_good["srs_retention_pct"] > r_due["srs_retention_pct"]
    assert r_good["readiness_score"] > r_due["readiness_score"]


def test_srs_session_api_queue_and_manual_review_e2e(isolated_client):
    client, db = isolated_client
    uid = 8809526955
    db.get_or_create_user(uid, username="sm2_driver")

    with db._get_connection() as conn:
        db._ensure_srs_schema(conn)
        conn.execute("DELETE FROM user_question_srs WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM session_answers WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_mistakes WHERE user_id = ?", (uid,))
        conn.commit()

    # 1. Seed 5 overdue SM-2 items + 6 mastered/fresh answered items (11 unique answered >= 10)
    past_due = (datetime.utcnow() - timedelta(hours=3)).isoformat()
    past_rev = (datetime.utcnow() - timedelta(days=2)).isoformat()
    due_qids = [f"CANON-YHQ-000{i}" for i in range(1, 6)]
    other_ok_qids = [f"CANON-YHQ-00{i}" for i in range(10, 16)]

    sess_seed = db.create_session(uid, "CATEGORY", "uz_latn", due_qids + other_ok_qids, category_id=1)
    for qid in other_ok_qids:
        db.process_session_answer(sess_seed["session_id"], uid, qid, "A", "A", True, "CATEGORY", response_time_ms=4000)
    for qid in due_qids:
        db.process_session_answer(sess_seed["session_id"], uid, qid, "B", "A", False, "CATEGORY", response_time_ms=3000)

    with db._get_connection() as conn:
        for qid in due_qids:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_question_srs (
                    user_id, canonical_id, ease_factor, interval_days, repetitions, lapses,
                    last_quality, last_reviewed_at, next_review_at
                ) VALUES (?, ?, 2.1, 0, 0, 1, 2, ?, ?)
                """,
                (uid, qid, past_rev, past_due),
            )
        conn.commit()

    # Verify /api/srs/queue shows all 5 due_now items prioritized cleanly
    q_res = client.get("/api/srs/queue?lang=uz_latn&limit=15")
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["ok"] is True
    assert q_data["summary"]["due_now_count"] == 5
    assert set(due_qids).issubset(set(q_data["due_question_ids"]))

    # Verify /api/learning/analytics recommends 'srs_review'
    ana = client.get("/api/learning/analytics?lang=uz_latn")
    assert ana.status_code == 200
    ana_data = ana.json()
    assert ana_data["srs_summary"]["due_now_count"] == 5
    assert ana_data["recommendation"]["kind"] == "srs_review"
    assert ana_data["recommendation"]["target_type"] == "SRS"

    # 2. Start daily SRS ("Aqlli Takrorlash") session -> prioritizes the 5 overdue items at the front
    start_srs = client.post("/api/session/start", json={
        "session_type": "SRS",
        "total_questions": 10,
        "language": "uz_latn",
    })
    assert start_srs.status_code == 200
    srs_sess = start_srs.json()
    assert srs_sess["session_type"] == "SRS"
    assert srs_sess["total_questions"] == 10
    assert srs_sess["queue_breakdown"]["due_srs"] == 5
    returned_first_5 = [q["canonical_id"] for q in srs_sess["questions"][:5]]
    assert set(returned_first_5) == set(due_qids)
    assert "srs_meta" in srs_sess["questions"][0]

    # 3. Answer first due item quickly & accurately -> promotes to interval_days=1 and drops due_now_count
    q0 = srs_sess["questions"][0]
    ans_res = client.post("/api/session/answer", json={
        "session_id": srs_sess["session_id"],
        "canonical_id": q0["canonical_id"],
        "selected_key": q0["correct_option_key"],
        "language": "uz_latn",
        "response_time_ms": 3500,
    })
    assert ans_res.status_code == 200
    ans_json = ans_res.json()
    assert ans_json["srs"]["interval_days"] == 1
    assert ans_json["srs"]["repetitions"] == 1
    assert ans_json["srs"]["last_quality"] == 5

    # 4. Manual flashcard confidence rating endpoint (POST /api/srs/review)
    rev_res = client.post("/api/srs/review", json={
        "canonical_id": q0["canonical_id"],
        "quality": 5,
    })
    assert rev_res.status_code == 200
    assert rev_res.json()["srs"]["repetitions"] == 2
    assert rev_res.json()["srs"]["interval_days"] == 6

    # Invalid canonical_id -> 404, invalid quality -> 422
    assert client.post("/api/srs/review", json={"canonical_id": "NON_EXISTENT", "quality": 4}).status_code == 404
    assert client.post("/api/srs/review", json={"canonical_id": q0["canonical_id"], "quality": 9}).status_code == 422

    # Check queue reduced by 1
    q_after = client.get("/api/srs/queue?lang=uz_latn").json()
    assert q_after["summary"]["due_now_count"] == 4


def test_phase5_frontend_hooks_and_trilingual_i18n_parity():
    prep_js = (ROOT_DIR / "static" / "js" / "views" / "prepare.js").read_text(encoding="utf-8")
    assert "btn-launch-srs" in prep_js
    assert "/api/srs/queue" in prep_js
    assert "session_type: 'SRS'" in prep_js

    quiz_js = (ROOT_DIR / "static" / "js" / "views" / "quiz.js").read_text(encoding="utf-8")
    assert "response_time_ms" in quiz_js
    assert "/api/srs/review" in quiz_js
    assert "data-srs-rate" in quiz_js

    home_js = (ROOT_DIR / "static" / "js" / "views" / "home.js").read_text(encoding="utf-8")
    assert "srs_review" in home_js
    assert "session_type: 'SRS'" in home_js

    trans_js = (ROOT_DIR / "static" / "js" / "translations.js").read_text(encoding="utf-8")
    for key in (
        "srs_mode_title:",
        "srs_due_now_lbl:",
        "srs_mastered_lbl:",
        "btn_start_srs:",
        "srs_next_days:",
        "rec_srs_review_title:",
        "srs_rate_hard:",
        "milestone_memory_master:",
    ):
        assert len(re.findall(rf"\b{re.escape(key)}", trans_js)) == 3, f"Expected 3-language coverage for {key}"
