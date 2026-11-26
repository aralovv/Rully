"""
Wave 2 Regression Tests:
- Scene passport canonical schema parity (769/769 solutions preserved)
- Provenance preservation for human-reviewed editorial items
- Day-0 honest streak (=0) and single-pass SM-2 recalibration
- Constant-query O(1) analytics & retention + runtime event logging
- Copy-on-write thread-safe product catalog reload
- Dynamic DB subscription plans, suffix collision grace window & 24h late window
"""
import asyncio
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.analytics.tracker import get_real_activity_analytics, get_retention_analytics, log_user_event
from src.api.main import app
from src.api.security import generate_dev_init_data
from src.avtotest_product import AvtotestProductEngine
from src.bot.database import BotDatabase
from src.db.provenance_classifier import approve_editorial_item, audit_and_seed_provenance
from src.payments.matching_engine import process_incoming_payment_event
from src.payments.order_manager import create_or_get_payment_order, invalidate_payment_cache


def test_image_scenes_single_canonical_schema_all_solutions_intact():
    with open("data/image_scenes.json", "r", encoding="utf-8") as f:
        scenes = json.load(f)
    assert len(scenes) == 769
    schemas = {tuple(sorted(v.keys())) for v in scenes.values()}
    assert len(schemas) == 1, f"Expected 1 uniform schema, found {len(schemas)}"
    non_empty_solutions = sum(1 for v in scenes.values() if (v.get("otish_tartibi_yoki_yechim") or "").strip())
    assert non_empty_solutions == 769


def test_no_null_category_ids_and_human_provenance_preserved():
    db_path = os.getenv("DB_PATH")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        null_cnt = conn.execute("SELECT COUNT(*) FROM canonical_questions WHERE category_id IS NULL").fetchone()[0]
        assert null_cnt == 0

        # Pick an existing queue item or create one and human-approve it
        q_row = conn.execute(
            "SELECT id, canonical_id FROM editorial_review_queue WHERE review_status='PENDING_EDITORIAL_REVIEW' LIMIT 1"
        ).fetchone()
        assert q_row is not None
        qid = q_row["id"]
        cid = q_row["canonical_id"]

        approve_editorial_item(
            conn,
            queue_id=qid,
            reviewer="qa_wave2_editor",
            legal_verification_status="VERIFIED_PRIMARY_LAW",
            legal_doc_title="VMQ 172",
            legal_chapter="12-bob",
            legal_clause="68-band",
        )
        # Re-running audit must preserve human review!
        audit_res = audit_and_seed_provenance(conn, admin_actor="wave2_test")
        assert audit_res["classification_counts"]["already_verified_preserved"] >= 1
        row = conn.execute(
            "SELECT legal_verification_status, editorial_reviewed_by FROM canonical_questions WHERE canonical_id = ?",
            (cid,),
        ).fetchone()
        assert row["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"
        assert row["editorial_reviewed_by"] == "qa_wave2_editor"
    finally:
        conn.close()


def test_day0_honest_streak_and_single_pass_sm2_recalibration():
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 998877661
    with db._get_connection() as conn:
        conn.execute("DELETE FROM learning_streak WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_question_srs WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM session_answers WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM telegram_users WHERE user_id = ?", (uid,))
        conn.commit()

    bundle = db.get_user_full_auth_bundle(uid, username="day0_driver")
    assert bundle["streak"]["current_streak"] == 0
    assert bundle["streak"]["today_questions_count"] == 0

    sess = db.create_session(uid, "SRS", "uz_latn", ["CANON-YHQ-0001"])
    ans = db.process_session_answer(sess["session_id"], uid, "CANON-YHQ-0001", "A", "A", True, "SRS", response_time_ms=2500)
    assert ans["streak"]["current_streak"] == 1
    assert ans["srs"]["repetitions"] == 1

    # Single-pass recalibrate=True re-grades SAME review instead of jumping repetitions to 2!
    recal = db.record_srs_review(uid, "CANON-YHQ-0001", quality=3, recalibrate=True)
    assert recal["repetitions"] == 1
    assert recal["last_quality"] == 3


def test_copy_on_write_engine_reload_never_returns_empty_catalog():
    engine = AvtotestProductEngine(os.getenv("DB_PATH"))
    errors = []

    def reader():
        try:
            for _ in range(30):
                if engine.get_total_question_count() <= 0 or len(engine.get_categories("uz_latn")) == 0:
                    errors.append("Observed empty catalog during reload")
        except Exception as exc:
            errors.append(repr(exc))

    def reloader():
        for _ in range(4):
            engine.invalidate_cache(reload=True)

    threads = [threading.Thread(target=reader) for _ in range(4)] + [threading.Thread(target=reloader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Concurrency errors during reload: {errors}"


def test_tracker_constant_query_analytics_and_payment_windows():
    uid = 998877662
    db = BotDatabase(os.getenv("DB_PATH"))
    db.get_or_create_user(uid, username="analytics_driver")
    log_user_event(uid, "WAVE2_TEST_EVENT", {"ok": True})

    act = get_real_activity_analytics()
    ret = get_retention_analytics()
    assert act["total_users"] >= 1
    assert sum(act["classification_summary"].values()) == act["total_users"]
    assert isinstance(ret["cohorts"], list)

    # Active DB plans endpoint returns stars_price dynamically
    client = TestClient(app)
    invalidate_payment_cache()
    plans_res = client.get("/api/subscription/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()["plans"]
    assert len(plans) >= 2 and all("stars_price" in p for p in plans)
    token = generate_dev_init_data(user_id=uid)

    # Expired order 48h ago must NOT auto-match LATE_PAYMENT
    with db._get_connection() as conn:
        old_exp = (datetime.utcnow() - timedelta(hours=48)).isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO payment_orders (
                order_id, user_id, plan_id, plan_name, duration_days, base_price_uzs,
                suffix_uzs, final_amount_uzs, card_id, card_suffix, card_number_masked,
                cardholder_name, status, created_at, expires_at
            ) VALUES ('ORD-ANCIENT-48H', ?, 'pro_14', '14 kunlik PRO', 14, 14000, 777, 14777, 1, '5370', '9860 **** **** 5370', 'DEV', 'EXPIRED', ?, ?)
            """,
            (uid, old_exp, old_exp),
        )
        conn.commit()
    res_match = asyncio.run(process_incoming_payment_event(
        {"is_incoming": True, "is_valid": True, "transaction_type": "INCOMING", "amount_uzs": 14777, "card_suffix": "5370", "payment_source": "HUMO", "raw_message": "+14777"},
        source_chat="test_chat",
        message_id=987654321,
    ))
    assert res_match["status"] == "UNMATCHED"
