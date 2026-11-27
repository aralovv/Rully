"""
RULLY 2.0 Phase 6 Verification Tests (Isolated tmp_path SQLite + TestClient + Aiogram mocks):
- Pillar 1: AI Ustoz Legal Provenance & Anti-Hallucination Guardrails (PROMPTS, TOOLS, GEMINI_SERVICE)
- Pillar 2: Payment Unmatched Near-Match Diagnostics, Atomic Order Linking, Reconciliation Health & MTProto Telemetry
- Pillar 3: Telegram Bot UX Parity (Deep Links, SM-2 /srs & /bilet Inline Handlers, Quiz SM-2 Sync) + SPA Deep-Link Routing
"""

import asyncio
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ai.gemini_service import GeminiService
from src.ai.prompts import get_system_prompt
from src.ai.tools import (
    GEMINI_TOOLS_DECLARATIONS,
    TOOL_MAPPING,
    format_legal_provenance_payload,
    get_provenance_select_sql,
    tool_get_srs_review_queue,
    tool_get_user_mistakes,
    tool_get_user_statistics,
    tool_search_questions,
)
from src.api.main import app
from src.avtotest_product import AvtotestProductEngine
from src.bot.database import BotDatabase
from src.bot.handlers.practice import cmd_bilet, start_bilet_callback, start_srs_review_flow
from src.bot.handlers.quiz import cb_submit_answer
from src.bot.handlers.start import build_deep_link_response
from src.bot.keyboards import (
    build_webapp_route_url,
    get_bilet_selection_keyboard,
    get_help_sections_keyboard,
)
from src.bot.rich_messages import format_rich_question
from src.db.migrations_v2 import apply_all_migrations
from src.mtproto.service import MTProtoManager
from src.payments.matching_engine import (
    get_payment_reconciliation_health_sync,
    link_unmatched_to_order_sync,
    process_incoming_payment_event,
)
from src.security.crypto import generate_session_token

MASTER_DB = Path("master_database.sqlite")


def _make_isolated_db(tmp_path: Path, name: str = "phase6_test.sqlite") -> Path:
    db_file = tmp_path / name
    shutil.copy2(MASTER_DB, db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    apply_all_migrations(conn)
    conn.close()
    return db_file


def _connect_factory(db_file: Path):
    def _connect():
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        return conn

    return _connect


# ==============================================================================
# PILLAR 1: AI USTOZ LEGAL PROVENANCE & ANTI-HALLUCINATION GUARDRAILS
# ==============================================================================


def test_ai_prompts_enforce_legal_provenance_all_languages():
    for lang in ("uz_latn", "uz_cyrl", "ru"):
        prompt = get_system_prompt(lang)
        assert "UNRESOLVED_LEGAL_REVIEW" in prompt
        assert "VERIFIED_FIRST_AID_OR_TECH" in prompt
        assert "get_srs_review_queue" in prompt


def test_ai_tools_provenance_guardrails_and_srs_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    db = BotDatabase(str(db_file))
    uid = 990601
    db.get_or_create_user(uid, "ai_p6_user")

    conn_fn = _connect_factory(db_file)
    with conn_fn() as conn:
        rows = conn.execute("SELECT canonical_id FROM canonical_questions ORDER BY canonical_id LIMIT 3").fetchall()
        cid_verified = rows[0]["canonical_id"]
        cid_first_aid = rows[1]["canonical_id"]
        cid_unresolved = rows[2]["canonical_id"]

        conn.execute(
            """
            UPDATE canonical_questions
            SET legal_reference = 'VMQ 172, 11-bob, 78-band',
                legal_verification_status = 'VERIFIED_PRIMARY_LAW',
                legal_doc_title = 'VMQ 172',
                legal_chapter = '11-bob',
                legal_clause = '78-band'
            WHERE canonical_id = ?
            """,
            (cid_verified,),
        )
        conn.execute(
            """
            UPDATE canonical_questions
            SET legal_reference = 'Birinchi yordam',
                legal_verification_status = 'VERIFIED_FIRST_AID_OR_TECH',
                legal_doc_title = 'Tibbiy xavfsizlik',
                legal_chapter = NULL,
                legal_clause = NULL
            WHERE canonical_id = ?
            """,
            (cid_first_aid,),
        )
        conn.execute(
            """
            UPDATE canonical_questions
            SET legal_reference = 'Taxminiy eski havola 99.1',
                legal_verification_status = 'UNRESOLVED_LEGAL_REVIEW',
                legal_doc_title = NULL,
                legal_chapter = NULL,
                legal_clause = NULL
            WHERE canonical_id = ?
            """,
            (cid_unresolved,),
        )
        conn.execute(
            """
            UPDATE canonical_translations
            SET question_text = 'Phase6_Sentinel_Search_Token Unresolved Case?'
            WHERE canonical_id = ? AND language = 'uz_latn'
            """,
            (cid_unresolved,),
        )
        conn.execute(
            """
            UPDATE canonical_translations
            SET question_text = 'Phase6_Sentinel_Search_Token Verified Case?'
            WHERE canonical_id = ? AND language = 'uz_latn'
            """,
            (cid_verified,),
        )
        conn.commit()

    # Record a mistake + SM-2 reviews (1 due overdue, 1 mastered future)
    db.record_mistake(uid, cid_unresolved)
    past_dt = datetime.utcnow() - timedelta(days=2)
    db.record_srs_review(uid, cid_unresolved, quality=1, now_dt=past_dt)
    future_dt = datetime.utcnow() - timedelta(days=30)
    for step in range(4):
        db.record_srs_review(uid, cid_verified, quality=5, now_dt=future_dt + timedelta(days=step * 2))

    # Ensure declarations and tool mapping include SM-2 queue
    assert any(d["name"] == "get_srs_review_queue" for d in GEMINI_TOOLS_DECLARATIONS)
    assert "get_srs_review_queue" in TOOL_MAPPING

    with patch("src.ai.tools.get_db_connection", side_effect=conn_fn):
        search_res = tool_search_questions("Phase6_Sentinel_Search_Token", limit=5, language="uz_latn")
        assert search_res["count"] == 2
        by_id = {q["canonical_id"]: q for q in search_res["questions"]}

        # Verified item keeps real VMQ clause
        assert by_id[cid_verified]["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"
        assert by_id[cid_verified]["legal_reference"] == "VMQ 172, 11-bob, 78-band"
        assert by_id[cid_verified]["legal_chapter"] == "11-bob"
        assert by_id[cid_verified]["legal_clause"] == "78-band"

        # Unresolved item masks unverified legal_reference and emits guardrail note
        assert by_id[cid_unresolved]["legal_verification_status"] == "UNRESOLVED_LEGAL_REVIEW"
        assert by_id[cid_unresolved]["legal_reference"] is None
        assert "UNRESOLVED_LEGAL_REVIEW" in by_id[cid_unresolved]["legal_guardrail_note"]

        # Mistakes tool includes provenance
        mistakes_res = tool_get_user_mistakes(uid, limit=5, language="uz_latn")
        assert mistakes_res["count"] == 1
        assert mistakes_res["mistake_questions"][0]["legal_verification_status"] == "UNRESOLVED_LEGAL_REVIEW"
        assert mistakes_res["mistake_questions"][0]["legal_reference"] is None

        # User stats include SM-2 telemetry
        stats_res = tool_get_user_statistics(uid, language="uz_latn")
        assert stats_res["srs_tracked_total"] == 2
        assert stats_res["srs_due_now"] >= 1
        assert "srs_retention_pct" in stats_res

        # SRS queue returns due item first with provenance metadata
        srs_res = tool_get_srs_review_queue(uid, limit=5, language="uz_latn")
        assert srs_res["count"] == 2
        assert srs_res["due_count"] >= 1
        assert srs_res["srs_items"][0]["canonical_id"] == cid_unresolved
        assert srs_res["srs_items"][0]["is_due"] is True
        assert srs_res["srs_items"][0]["legal_reference"] is None

    # Minimal legacy v1 schema missing provenance columns must still work safely
    legacy_db = sqlite3.connect(":memory:")
    legacy_db.execute("CREATE TABLE canonical_questions (canonical_id TEXT)")
    sql_expr = get_provenance_select_sql(legacy_db, "cq")
    assert "NULL AS legal_verification_status" in sql_expr
    legacy_db.close()

    # Check first-aid formatting rule
    fa = format_legal_provenance_payload({
        "legal_verification_status": "VERIFIED_FIRST_AID_OR_TECH",
        "legal_reference": "Birinchi yordam",
    })
    assert fa["legal_verification_status"] == "VERIFIED_FIRST_AID_OR_TECH"
    assert "VMQ 172 moddasi emas" in fa["legal_guardrail_note"]


def test_ai_gemini_service_guardrail_blocks_unverified_vmq_hallucination(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-phase6")
    db_file = _make_isolated_db(tmp_path)
    db = BotDatabase(str(db_file))
    uid = 990602
    db.get_or_create_user(uid, "ai_guard_user")

    conn_fn = _connect_factory(db_file)
    with conn_fn() as conn:
        rows = conn.execute("SELECT canonical_id FROM canonical_questions ORDER BY canonical_id LIMIT 2").fetchall()
        cid_unresolved = rows[0]["canonical_id"]
        cid_verified = rows[1]["canonical_id"]
        conn.execute(
            """
            UPDATE canonical_questions
            SET legal_reference = 'Taxminiy 88-band',
                legal_verification_status = 'UNRESOLVED_LEGAL_REVIEW',
                legal_doc_title = NULL,
                legal_chapter = NULL,
                legal_clause = NULL
            WHERE canonical_id = ?
            """,
            (cid_unresolved,),
        )
        conn.execute(
            """
            UPDATE canonical_questions
            SET legal_reference = 'VMQ 172, 22-bob, 152-band',
                legal_verification_status = 'VERIFIED_PRIMARY_LAW',
                legal_doc_title = 'VMQ 172',
                legal_chapter = '22-bob',
                legal_clause = '152-band'
            WHERE canonical_id = ?
            """,
            (cid_verified,),
        )
        conn.commit()

    db.record_srs_review(uid, cid_unresolved, quality=1, now_dt=datetime.utcnow() - timedelta(days=1))
    snapshot = db.get_ai_student_snapshot(uid)
    assert snapshot["srs_tracked_total"] == 1
    assert snapshot["srs_due_now"] == 1

    service = GeminiService()
    learner_txt = service._build_learner_context(snapshot)
    assert "Aqlli Takrorlash (SM-2)" in learner_txt
    assert "muddati kelgan 1 ta" in learner_txt

    with patch("src.ai.gemini_service.get_db_connection", side_effect=conn_fn), patch(
        "src.ai.tools.get_db_connection", side_effect=conn_fn
    ):
        gt_unres = service._build_ground_truth_context(None, cid_unresolved, "uz_latn")
        assert "UNRESOLVED_LEGAL_REVIEW" in gt_unres
        assert "Taxminiy 88-band" not in gt_unres

        gt_ver = service._build_ground_truth_context(None, cid_verified, "uz_latn")
        assert "VERIFIED_PRIMARY_LAW" in gt_ver
        assert "22-bob" in gt_ver

        # Simulated LLM hallucinates "VMQ 172 14.2-band" on an UNRESOLVED item -> guardrail catches it
        hallucinated_resp = (
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "VMQ 172 14.2-band talabiga ko'ra bu yerda to'xtash mumkin emas."}
                            ]
                        }
                    }
                ]
            },
            200,
            None,
        )
        with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(return_value=hallucinated_resp)):
            out = asyncio.run(
                service.chat(
                    user_id=uid,
                    session_id="guard-unres",
                    message="Nega bunday?",
                    is_pro=True,
                    language="uz_latn",
                    canonical_id=cid_unresolved,
                    student_snapshot=snapshot,
                )
            )
            assert out["ok"] is True
            assert out["grounding"]["legal_verification_status"] == "UNRESOLVED_LEGAL_REVIEW"
            assert out["grounding"]["citation_flagged"] is True
            assert "tekshiruvda" in out["reply"].lower()

        # Tool loop with get_srs_review_queue populates cards cleanly on a verified item
        tool_r1 = (
            {
                "candidates": [
                    {"content": {"parts": [{"functionCall": {"name": "get_srs_review_queue", "args": {"limit": 3}}}]}}
                ]
            },
            200,
            None,
        )
        tool_r2 = (
            {
                "candidates": [
                    {"content": {"parts": [{"text": "VMQ 172 22-bob 152-band asosida tezlik cheklanadi."}]}}
                ]
            },
            200,
            None,
        )
        with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(side_effect=[tool_r1, tool_r2])):
            out2 = asyncio.run(
                service.chat(
                    user_id=uid,
                    session_id="guard-ver",
                    message="Takrorlash rejam qanday?",
                    is_pro=True,
                    language="uz_latn",
                    canonical_id=cid_verified,
                    student_snapshot=snapshot,
                )
            )
            assert out2["ok"] is True
            assert out2["grounding"]["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"
            assert out2["grounding"]["citation_flagged"] is False
            assert len(out2["cards"]) == 1
            assert out2["cards"][0]["canonical_id"] == cid_unresolved


# ==============================================================================
# PILLAR 2: PAYMENT RECONCILIATION DIAGNOSTICS & MTPROTO HEALTH OBSERVABILITY
# ==============================================================================


def test_payment_unmatched_diagnostics_atomic_linking_and_health_api(tmp_path, monkeypatch):
    import src.admin.auth_service as admin_auth
    import src.admin.routes_admin_payments as rap
    import src.payments.matching_engine as me

    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    conn_fn = _connect_factory(db_file)
    monkeypatch.setattr(me, "DB_PATH", str(db_file))
    monkeypatch.setattr(me, "_get_connection", conn_fn)
    monkeypatch.setattr(rap, "DB_PATH", str(db_file))
    monkeypatch.setattr(rap, "_get_connection", conn_fn)
    monkeypatch.setattr(admin_auth, "DB_PATH", str(db_file))

    uid = 990610
    uid2 = 990611
    uid3 = 990612
    order_card_mismatch = "ORD-P6-CARD-1"
    order_near_amt = "ORD-P6-AMT-2"
    order_expired = "ORD-P6-EXP-3"
    now_str = datetime.utcnow().isoformat()
    exp_future = (datetime.utcnow() + timedelta(minutes=25)).isoformat()
    exp_past = (datetime.utcnow() - timedelta(minutes=30)).isoformat()

    admin_token = generate_session_token()
    with conn_fn() as conn:
        for test_uid, uname in ((uid, "pay_p6_1"), (uid2, "pay_p6_2"), (uid3, "pay_p6_3")):
            conn.execute(
                """
                INSERT INTO telegram_users (user_id, username, first_name, is_pro, created_at, last_active_at)
                VALUES (?, ?, 'PayUser', 0, ?, ?)
                """,
                (test_uid, uname, now_str, now_str),
            )
        conn.execute(
            """
            INSERT INTO payment_orders (
                order_id, user_id, plan_id, plan_name, duration_days, base_price_uzs,
                suffix_uzs, final_amount_uzs, card_id, card_suffix, card_number_masked, cardholder_name, status, created_at, expires_at
            ) VALUES (?, ?, 'pro_14d', '14 kunlik', 14, 14000, 55, 14055, 1, '1234', '9860****1234', 'TEST CARD', 'PENDING', ?, ?)
            """,
            (order_card_mismatch, uid, now_str, exp_future),
        )
        conn.execute(
            """
            INSERT INTO payment_orders (
                order_id, user_id, plan_id, plan_name, duration_days, base_price_uzs,
                suffix_uzs, final_amount_uzs, card_id, card_suffix, card_number_masked, cardholder_name, status, created_at, expires_at
            ) VALUES (?, ?, 'pro_30d', '30 kunlik', 30, 25000, 123, 25123, 1, '4321', '9860****4321', 'TEST CARD', 'PENDING', ?, ?)
            """,
            (order_near_amt, uid2, now_str, exp_future),
        )
        conn.execute(
            """
            INSERT INTO payment_orders (
                order_id, user_id, plan_id, plan_name, duration_days, base_price_uzs,
                suffix_uzs, final_amount_uzs, card_id, card_suffix, card_number_masked, cardholder_name, status, created_at, expires_at
            ) VALUES (?, ?, 'pro_30d', '30 kunlik', 30, 25000, 222, 25222, 1, '7777', '9860****7777', 'TEST CARD', 'EXPIRED', ?, ?)
            """,
            (order_expired, uid3, exp_past, exp_past),
        )
        admin_id = conn.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'").fetchone()[0]
        conn.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', datetime('now'), datetime('now', '+2 hours'), 0, datetime('now'))
            """,
            (admin_token, admin_id),
        )
        conn.commit()

    unmatched_alert_mock = AsyncMock(return_value=True)
    with patch("src.payments.matching_engine.send_unmatched_payment_alert", new=unmatched_alert_mock):
        # Case 1: Card suffix mismatch
        res1 = asyncio.run(
            process_incoming_payment_event(
                {
                    "is_incoming": True,
                    "amount_uzs": 14055,
                    "balance_uzs": 50000,
                    "card_suffix": "9999",
                    "payment_source": "Click",
                    "raw_timestamp": "01:00",
                    "raw_message": "Popolnenie 14055 *9999",
                },
                message_id=6001,
            )
        )
        assert res1["status"] == "UNMATCHED"
        assert res1["diagnostic"]["reason_code"] == "CARD_SUFFIX_MISMATCH"
        assert res1["diagnostic"]["candidate_order_id"] == order_card_mismatch
        assert unmatched_alert_mock.await_args.kwargs["candidate_order_id"] == order_card_mismatch

        # Case 2: Near amount pending
        res2 = asyncio.run(
            process_incoming_payment_event(
                {
                    "is_incoming": True,
                    "amount_uzs": 25000,
                    "balance_uzs": 75000,
                    "card_suffix": "4321",
                    "payment_source": "Payme",
                    "raw_timestamp": "01:01",
                    "raw_message": "Popolnenie 25000 *4321",
                },
                message_id=6002,
            )
        )
        assert res2["status"] == "UNMATCHED"
        assert res2["diagnostic"]["reason_code"] == "NEAR_AMOUNT_PENDING"
        assert res2["diagnostic"]["candidate_order_id"] == order_near_amt

        # Case 3: Expired near match
        res3 = asyncio.run(
            process_incoming_payment_event(
                {
                    "is_incoming": True,
                    "amount_uzs": 25000,
                    "balance_uzs": 100000,
                    "card_suffix": "7777",
                    "payment_source": "Humo",
                    "raw_timestamp": "01:02",
                    "raw_message": "Popolnenie 25000 *7777",
                },
                message_id=6003,
            )
        )
        assert res3["status"] == "UNMATCHED"
        assert res3["diagnostic"]["reason_code"] == "EXPIRED_NEAR_MATCH"
        assert res3["diagnostic"]["candidate_order_id"] == order_expired

    with conn_fn() as conn:
        first_unmatched = conn.execute(
            "SELECT id FROM unmatched_payments WHERE status = 'UNRESOLVED' ORDER BY id ASC LIMIT 1"
        ).fetchone()["id"]

    # Admin links unmatched payment to pending order atomically via API
    client = TestClient(app)
    with patch("src.admin.routes_admin_payments.send_user_payment_success_notification", new=AsyncMock(return_value=True)), patch(
        "src.admin.routes_admin_payments.send_late_payment_approved_alert", new=AsyncMock(return_value=True)
    ):
        link_res = client.post(
            f"/api/admin/payments/unmatched/{first_unmatched}/link-order",
            json={"order_id": order_card_mismatch, "notes": "Verified user card receipt"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert link_res.status_code == 200
        body = link_res.json()
        assert body["ok"] is True
        assert body["order_id"] == order_card_mismatch
        assert body["user_id"] == uid

    with conn_fn() as conn:
        u_row = conn.execute("SELECT is_pro, subscription_tier FROM telegram_users WHERE user_id = ?", (uid,)).fetchone()
        assert u_row["is_pro"] == 1
        assert u_row["subscription_tier"] == "pro_14d"

        tx_count = conn.execute(
            "SELECT COUNT(*) FROM payment_transactions WHERE order_id = ?", (order_card_mismatch,)
        ).fetchone()[0]
        assert tx_count == 1

    # Reconciliation + MTProto health API
    health_res = client.get("/api/admin/payments/health", headers={"Authorization": f"Bearer {admin_token}"})
    assert health_res.status_code == 200
    hdata = health_res.json()
    assert hdata["ok"] is True
    assert hdata["reconciliation"]["matched_events"] == 1
    assert hdata["reconciliation"]["ledger_transactions"] == 1
    assert hdata["reconciliation"]["discrepancy_count"] == 0
    assert hdata["reconciliation"]["is_balanced"] is True
    assert hdata["reconciliation"]["unresolved_unmatched"] == 2
    assert "is_live_connected" in hdata["mtproto"]
    assert "can_accept_simulated_events" in hdata["mtproto"]

    # Direct negative lookup raises cleanly
    with pytest.raises(ValueError):
        link_unmatched_to_order_sync(999999, order_near_amt, 1, "Anvarjon", "missing")

    # Direct health helper matches
    rec = get_payment_reconciliation_health_sync()
    assert rec["is_balanced"] is True


def test_mtproto_manager_status_reflects_real_connection_state(tmp_path, monkeypatch):
    db_file = _make_isolated_db(tmp_path)
    conn_fn = _connect_factory(db_file)
    monkeypatch.setattr("src.mtproto.service.DB_PATH", str(db_file))
    monkeypatch.setattr("src.mtproto.service.get_active_orders_count", lambda: 4)

    mgr = MTProtoManager()
    mgr._get_connection = conn_fn
    mgr.connection_status = "DISCONNECTED"
    status_disc = mgr.get_status()
    assert status_disc["is_ready_for_matching"] is False
    assert status_disc["is_live_connected"] is False
    assert status_disc["can_accept_simulated_events"] is True
    assert status_disc["active_orders_count"] == 4

    mgr.connection_status = "CONNECTED"
    status_conn = mgr.get_status()
    assert status_conn["is_ready_for_matching"] is True
    assert status_conn["is_live_connected"] is True


# ==============================================================================
# PILLAR 3: TELEGRAM BOT UX PARITY & SPA DEEP-LINK ROUTING
# ==============================================================================


def test_bot_deep_links_all_targets_and_languages(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    db = BotDatabase(str(db_file))
    uid = 990620
    db.get_or_create_user(uid, "bot_dl_user")
    db.record_srs_review(uid, "CANON-YHQ-0001", quality=1, now_dt=datetime.utcnow() - timedelta(days=1))

    assert "?route=srs#srs" in build_webapp_route_url("srs")
    assert "?route=bilet_5#bilet_5" in build_webapp_route_url("bilet_5")

    for lang in ("uz_latn", "uz_cyrl", "ru"):
        for target in ("amaliy", "srs", "takrorlash", "bilet_5", "ticket_12", "exam", "signs", "rules", "ai", "mistakes", "profile", "tests"):
            res = build_deep_link_response(target, lang, db, uid)
            assert res is not None, f"Deep link '{target}' returned None for {lang}"
            text, kb = res
            assert len(text) > 10
            btns = [b for row in kb.inline_keyboard for b in row]
            assert any(b.web_app and b.web_app.url for b in btns)

        # Verify rich card headers exist in all languages
        q_html = format_rich_question(
            session_type="SRS",
            current_index=1,
            total_questions=5,
            category_name="Umumiy qoidalar",
            question_text="Test savol?",
            options=[{"key": "A", "text": "Javob A"}],
            language=lang,
        )
        assert "[" not in q_html[:120]
        assert "SM-2" in q_html

    assert build_deep_link_response("", "uz_latn", db, uid) is None
    assert build_deep_link_response("unknown_arg_xyz", "uz_latn", db, uid) is None


def test_bot_srs_bilet_handlers_and_quiz_sm2_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    db = BotDatabase(str(db_file))
    engine = AvtotestProductEngine(str(db_file))
    uid = 990621
    db.get_or_create_user(uid, "bot_quiz_user", default_lang="uz_latn")

    # Keyboard pagination & Help hub checks
    bilet_kb_p0 = get_bilet_selection_keyboard(total_tickets=67, page=0, language="uz_latn")
    callbacks_p0 = [b.callback_data for row in bilet_kb_p0.inline_keyboard for b in row if b.callback_data]
    assert "bilet:start:1" in callbacks_p0
    assert "bilet:start:10" in callbacks_p0
    assert "bilet:page:1" in callbacks_p0

    bilet_kb_last = get_bilet_selection_keyboard(total_tickets=67, page=6, language="ru")
    callbacks_last = [b.callback_data for row in bilet_kb_last.inline_keyboard for b in row if b.callback_data]
    assert "bilet:start:67" in callbacks_last
    assert "bilet:page:5" in callbacks_last

    help_kb = get_help_sections_keyboard("uz_latn")
    help_callbacks = [b.callback_data for row in help_kb.inline_keyboard for b in row if b.callback_data]
    assert "menu:srs" in help_callbacks
    assert "menu:bilets" in help_callbacks

    # Mock Bot + render_session_question capture
    rendered = []

    async def _fake_render(bot_obj, chat_id, session, product_engine, database):
        rendered.append(session)

    mock_bot = SimpleNamespace(
        send_message=AsyncMock(),
        send_photo=AsyncMock(),
    )

    msg_obj = SimpleNamespace(
        from_user=SimpleNamespace(id=uid),
        chat=SimpleNamespace(id=uid),
        answer=AsyncMock(),
    )

    with patch("src.bot.handlers.practice.render_session_question", side_effect=_fake_render):
        # 1. Empty SM-2 queue sends friendly card instead of failing
        asyncio.run(start_srs_review_flow(msg_obj, mock_bot, engine, db))
        assert msg_obj.answer.await_count == 1
        assert len(rendered) == 0

        # 2. Seed overdue SM-2 item -> launches native SRS session
        with sqlite3.connect(str(db_file)) as conn:
            sample_cid = conn.execute("SELECT canonical_id FROM canonical_questions ORDER BY canonical_id LIMIT 1").fetchone()[0]
        db.record_srs_review(uid, sample_cid, quality=1, now_dt=datetime.utcnow() - timedelta(days=2))

        asyncio.run(start_srs_review_flow(msg_obj, mock_bot, engine, db))
        assert len(rendered) == 1
        assert rendered[-1]["session_type"] == "SRS"
        assert sample_cid in rendered[-1]["question_ids"]

        # 3. /bilet 2 launches Ticket #2 directly (tracked as BILET)
        cmd_obj = SimpleNamespace(args="2")
        asyncio.run(cmd_bilet(msg_obj, cmd_obj, mock_bot, engine, db))
        assert rendered[-1]["session_type"] == "BILET"
        assert rendered[-1]["category_id"] == 2
        assert rendered[-1]["total_questions"] >= 10

        # 4. Callback bilet:start:3 launches Ticket #3
        cb_bilet = SimpleNamespace(
            data="bilet:start:3",
            from_user=SimpleNamespace(id=uid),
            message=SimpleNamespace(chat=SimpleNamespace(id=uid), answer=AsyncMock()),
            answer=AsyncMock(),
        )
        asyncio.run(start_bilet_callback(cb_bilet, mock_bot, engine, db))
        assert rendered[-1]["session_type"] == "BILET"
        assert rendered[-1]["category_id"] == 3

    # 5. Answering a question in Telegram Bot quiz syncs SM-2 user_question_srs
    active_sess = db.get_active_session(uid)
    first_cid = active_sess["question_ids"][0]
    q_item = engine.get_question(first_cid, language="uz_latn", include_answer_key=True)
    cb_ans = SimpleNamespace(
        data=f"ans:{active_sess['session_id']}:{q_item.correct_option_key}",
        from_user=SimpleNamespace(id=uid),
        message=SimpleNamespace(chat=SimpleNamespace(id=uid), text="Q", caption=None, edit_text=AsyncMock(), answer=AsyncMock()),
        answer=AsyncMock(),
    )
    asyncio.run(cb_submit_answer(cb_ans, mock_bot, engine, db))
    srs_map = db.get_question_srs_map(uid, [first_cid])
    assert first_cid in srs_map
    assert srs_map[first_cid]["last_quality"] == 4
    assert srs_map[first_cid]["repetitions"] >= 1


def test_spa_deep_link_hash_js_syntax_and_routing():
    chk = subprocess.run(["node", "--check", "static/js/app.js"], capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr

    # Node smoke verification of resolveDeepLinkRoute & applyDeepLinkRoute
    node_script = r"""
    const fs = require('fs');
    const code = fs.readFileSync('static/js/app.js', 'utf8');
    const navigated = [];
    const sessions = [];
    global.document = {
      readyState: 'complete',
      querySelectorAll: () => [],
      getElementById: () => null,
      addEventListener: () => {},
      body: { classList: { remove: () => {} } }
    };
    global.window = {
      RULLY: {
        state: { activeTab: 'home', prepareSubtab: 'topics', lang: 'uz_latn', ai: { loaded: true }, quiz: { active: false }, streak: {} },
        t: (k) => k,
        icon: () => '',
        escHtml: (s) => s,
        normalizeLang: (l) => l || 'uz_latn',
        resolveInitData: () => '',
        syncTelegramBackButton: () => {},
        syncShellUI: () => {},
        renderHome: () => {},
        renderPrepare: () => {},
        loadPrepareData: () => {},
        renderAmaliy: () => {},
        loadAmaliyData: () => {},
        renderAiView: () => {},
        renderProfile: () => {},
        loadAnalyticsAsync: () => {},
        initHudBindings: () => {},
        api: () => Promise.resolve({ user: { language: 'uz_latn' }, stats: {}, streak: {} }),
        theme: { init: () => {} },
        startSession: (cfg) => sessions.push(cfg),
      },
      location: { search: '?route=srs', hash: '#tgWebAppData=abc' },
      addEventListener: () => {},
    };
    eval(code);
    const R = global.window.RULLY;
    R.navigateTo = (tab) => navigated.push({ tab, sub: R.state.prepareSubtab });
    if (R.resolveDeepLinkRoute() !== 'srs') process.exit(2);
    if (!R.applyDeepLinkRoute('srs')) process.exit(3);
    if (!R.applyDeepLinkRoute('bilet_7')) process.exit(4);
    if (!R.applyDeepLinkRoute('signs')) process.exit(5);
    if (!R.applyDeepLinkRoute('rules')) process.exit(6);
    if (!R.applyDeepLinkRoute('amaliy')) process.exit(7);
    if (R.applyDeepLinkRoute('nonexistent_route')) process.exit(8);
    console.log(JSON.stringify({ navigated, sessions }));
    """
    run = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    parsed = json.loads(run.stdout.strip())
    assert {"tab": "tests", "sub": "drill"} in parsed["navigated"]
    assert {"tab": "tests", "sub": "tickets"} in parsed["navigated"]
    assert any(n.get("sub") in ("reference", "cheatsheet") for n in parsed["navigated"])
    assert any(n["tab"] == "amaliy" for n in parsed["navigated"])
    assert {"session_type": "BILET", "ticket_number": 7} in parsed["sessions"]
