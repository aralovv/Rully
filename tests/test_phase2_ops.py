"""
RULLY 2.0 Phase 2 Verification Tests (Isolated tmp_path SQLite + TestClient):
- R-05: canonical_bundle.json atomic export, SHA-256 verification, tamper fallback, drift reload, and degraded bundle mode
- R-03: Payment order_manager & matching_engine execute_batch() atomicity + fault-injection rollback
- U-02 / U-04: StagingManager + Editorial Queue 3-language & legal provenance enforcement + catalog_version bump
- U-03: Fail-closed GitHub Actions sync webhook auth (503 / 403 / 200)
- R-07: AST regression guard confirming async FastAPI routes never block the event loop with direct DB calls
"""

import ast
import glob
import json
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.avtotest_product import AvtotestProductEngine
from src.db.catalog_bundle import (
    get_db_catalog_revision,
    increment_catalog_version,
    verify_and_load_canonical_bundle,
    write_canonical_bundle_atomic,
)
from src.db.migrations_v2 import apply_phase1_migrations
from src.db.provenance_classifier import (
    approve_editorial_item,
    audit_and_seed_provenance,
    list_editorial_queue,
)
from src.security.crypto import generate_session_token
from src.sync.staging_manager import StagingManager

MASTER_DB = Path("master_database.sqlite")


def _make_isolated_db(tmp_path: Path, name: str = "phase2_test.sqlite") -> Path:
    db_file = tmp_path / name
    shutil.copy2(MASTER_DB, db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    apply_phase1_migrations(conn)
    conn.close()
    return db_file


def test_canonical_bundle_atomic_export_tamper_drift_and_degraded_fallback(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    out_dir = tmp_path / "bundle_out"

    # 1. Atomic export produces SHA-256 verified v2 bundle + manifest
    meta = write_canonical_bundle_atomic(str(db_file), out_dir=out_dir, verify_min_count=1295)
    bundle_path = Path(meta["bundle_path"])
    manifest_path = Path(meta["manifest_path"])
    assert bundle_path.exists()
    assert manifest_path.exists()
    assert meta["canonical_count"] == 1327

    bundle_data, err = verify_and_load_canonical_bundle(bundle_path)
    assert err is None
    assert bundle_data["schema_version"] == 2
    assert bundle_data["canonical_count"] == 1327

    # 2. Engine loads from verified bundle when db catalog_version aligns
    engine = AvtotestProductEngine(str(db_file), bundle_path=str(bundle_path))
    assert engine._cache_source == "bundle"
    assert len(engine._cache_questions) == 1327
    cats = engine.get_categories("uz_latn")
    assert len(cats) > 0

    # 3. Missing bundle falls back cleanly to SQL
    missing_engine = AvtotestProductEngine(str(db_file), bundle_path=str(tmp_path / "does_not_exist.json"))
    assert missing_engine._cache_source == "sql"
    assert len(missing_engine._cache_questions) == 1327

    # 4. Degraded SQL-unavailable mode uses verified bundle read-only instead of failing closed
    missing_db = tmp_path / "missing_sql.sqlite"
    degraded_engine = AvtotestProductEngine(str(missing_db), bundle_path=str(bundle_path))
    assert degraded_engine._cache_source == "bundle_degraded_sql_unavailable"
    assert len(degraded_engine._cache_questions) == 1327

    # 5. Tampered bundle triggers CATALOG_BUNDLE_STALE_FALLBACK -> live SQL fallback
    tampered = json.loads(bundle_path.read_text(encoding="utf-8"))
    original_q_text = tampered["questions"][0]["translations"]["uz_latn"]["question_text"]
    first_cid = tampered["questions"][0]["canonical_id"]
    tampered["questions"][0]["translations"]["uz_latn"]["question_text"] = "TAMPERED_TEXT"
    tampered_path = tmp_path / "tampered_bundle.json"
    tampered_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    t_loaded, t_err = verify_and_load_canonical_bundle(tampered_path)
    assert t_loaded is None
    assert t_err == "BUNDLE_SHA256_MISMATCH"

    caplog.clear()
    fallback_engine = AvtotestProductEngine(str(db_file), bundle_path=str(tampered_path))
    assert fallback_engine._cache_source == "sql"
    assert fallback_engine.get_question(first_cid, "uz_latn").question_text == original_q_text
    assert any("CATALOG_BUNDLE_STALE_FALLBACK" in r.message for r in caplog.records)

    # 6. Database catalog_version increment triggers automatic drift reload to SQL
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "UPDATE canonical_translations SET question_text = ? WHERE canonical_id = ? AND language = 'uz_latn'",
        ("UPDATED_CANON_TEXT_IN_SQL", first_cid),
    )
    conn.commit()
    new_rev = increment_catalog_version(conn)
    conn.close()
    assert new_rev >= 1

    drifted = engine.ensure_fresh_cache(force=True)
    assert drifted is True
    assert engine._cache_source == "sql"
    assert engine.get_question(first_cid, "uz_latn").question_text == "UPDATED_CANON_TEXT_IN_SQL"


def test_payment_order_and_matching_batch_atomicity_and_rollback(tmp_path, monkeypatch):
    import asyncio
    import src.payments.matching_engine as me
    import src.payments.order_manager as om

    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    monkeypatch.setattr(om, "DB_PATH", str(db_file))
    monkeypatch.setattr(me, "DB_PATH", str(db_file))

    test_uid = 991234567
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO telegram_users (user_id, username, first_name, is_pro, created_at, last_active_at)
            VALUES (?, 'pay_tester', 'PayTester', 0, datetime('now'), datetime('now'))
            """,
            (test_uid,),
        )
        conn.commit()

    # 1. Fault-injection in create_or_get_payment_order: fail on execute_batch -> zero orphan orders committed
    with patch.object(om, "execute_batch", side_effect=RuntimeError("Simulated batch abort")):
        with pytest.raises(RuntimeError, match="Simulated batch abort"):
            om.create_or_get_payment_order(test_uid, "pro_14")

    with sqlite3.connect(str(db_file)) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM payment_orders WHERE user_id = ?", (test_uid,)).fetchone()[0]
        assert cnt == 0

    # 2. Normal order creation succeeds atomically (order + activity event)
    om.invalidate_payment_cache()
    ok, _, order = om.create_or_get_payment_order(test_uid, "pro_14")
    assert ok is True
    order_id = order["order_id"]
    amount_uzs = order["final_amount_uzs"]
    card_suffix = order["card_suffix"]

    with sqlite3.connect(str(db_file)) as conn:
        evt_cnt = conn.execute(
            "SELECT COUNT(*) FROM user_activity_events WHERE user_id = ? AND event_name = 'PAYMENT_ORDER_CREATED'",
            (test_uid,),
        ).fetchone()[0]
        assert evt_cnt == 1

    parsed_exact = {
        "is_incoming": True,
        "amount_uzs": amount_uzs,
        "card_suffix": card_suffix,
        "payment_source": "HUMO",
        "timestamp_str": "26.11.2026 23:05",
        "raw_message": f"+{amount_uzs} UZS card *{card_suffix}",
        "balance_uzs": 500000,
    }

    # 3. Fault-injection in matching_engine batch -> zero partial writes (order stays PENDING, no event/tx/PRO)
    with patch.object(me, "execute_batch", side_effect=RuntimeError("Simulated ledger failure")):
        with pytest.raises(RuntimeError, match="Simulated ledger failure"):
            asyncio.run(me.process_incoming_payment_event(parsed_exact, message_id=7001))

    with sqlite3.connect(str(db_file)) as conn:
        ord_status = conn.execute("SELECT status FROM payment_orders WHERE order_id = ?", (order_id,)).fetchone()[0]
        pe_cnt = conn.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0]
        tx_cnt = conn.execute("SELECT COUNT(*) FROM payment_transactions WHERE order_id = ?", (order_id,)).fetchone()[0]
        is_pro = conn.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (test_uid,)).fetchone()[0]
        assert ord_status == "PENDING"
        assert pe_cnt == 0
        assert tx_cnt == 0
        assert is_pro == 0

    # 4. Real exact match commits all 7 tables atomically
    with patch.object(me, "send_user_payment_success_notification", new=AsyncMock()), \
         patch.object(me, "send_payment_alert_to_admin", new=AsyncMock()):
        res = asyncio.run(me.process_incoming_payment_event(parsed_exact, message_id=7001))
        assert res["status"] == "MATCHED"
        assert res["order_id"] == order_id

        # Duplicate replay is idempotent
        dup = asyncio.run(me.process_incoming_payment_event(parsed_exact, message_id=7001))
        assert dup["status"] == "DUPLICATE"

    with sqlite3.connect(str(db_file)) as conn:
        assert conn.execute("SELECT status FROM payment_orders WHERE order_id = ?", (order_id,)).fetchone()[0] == "PAID"
        assert conn.execute("SELECT COUNT(*) FROM payment_transactions WHERE order_id = ?", (order_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (test_uid,)).fetchone()[0] == 1

    # 5. Unmatched event creates atomic payment_events + unmatched_payments + admin_audit_logs
    parsed_unmatched = {
        "is_incoming": True,
        "amount_uzs": 987654,
        "card_suffix": card_suffix,
        "payment_source": "HUMO",
        "timestamp_str": "26.11.2026 23:06",
        "raw_message": f"+987654 UZS card *{card_suffix}",
    }
    with patch.object(me, "send_unmatched_payment_alert", new=AsyncMock()):
        un_res = asyncio.run(me.process_incoming_payment_event(parsed_unmatched, message_id=7002))
        assert un_res["status"] == "UNMATCHED"

    with sqlite3.connect(str(db_file)) as conn:
        u_row = conn.execute(
            "SELECT u.amount_uzs, e.status FROM unmatched_payments u JOIN payment_events e ON u.event_id = e.id WHERE u.amount_uzs = 987654"
        ).fetchone()
        assert u_row is not None
        assert u_row[1] == "UNMATCHED"


def test_staging_manager_3lang_legal_provenance_and_catalog_bump(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)

    with sqlite3.connect(str(db_file)) as conn:
        rev_before = get_db_catalog_revision(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO staged_questions (
                source_code, source_ticket, source_position, change_type,
                category_slug, category_name,
                text_uz_latn, text_uz_cyrl, text_ru,
                options_json, correct_option_key, explanation,
                review_status, created_at, updated_at
            ) VALUES (
                'propdd', 888, 1, 'NEW_QUESTION',
                'umumiy-qoidalar', 'Umumiy qoidalar',
                'Lotincha savol?', 'Кириллча савол?', 'Русский вопрос?',
                ?, 'A', 'Default expl',
                'PENDING_REVIEW', datetime('now'), datetime('now')
            )
            """,
            (json.dumps([
                {"key": "A", "is_correct": True, "text_uz_latn": "Ha", "text_uz_cyrl": "Ҳа", "text_ru": "Да"},
                {"key": "B", "is_correct": False, "text_uz_latn": "Yo'q", "text_uz_cyrl": "Йўқ", "text_ru": "Нет"},
            ]),),
        )
        staged_id = cur.lastrowid
        conn.commit()

    mgr = StagingManager(str(db_file), backup_dir=str(tmp_path / "bkp"))

    # Refusing primary law status without citation metadata
    with pytest.raises(ValueError, match="VERIFIED_PRIMARY_LAW requires"):
        mgr.edit_and_approve_question(
            staged_id,
            {"legal_verification_status": "VERIFIED_PRIMARY_LAW", "legal_doc_title": ""},
            admin_username="QA_Admin",
        )

    # Full 3-language explanation + verified legal provenance succeeds and bumps catalog_version
    res = mgr.edit_and_approve_question(
        staged_id,
        {
            "explanation_uz_latn": "YHQ 3-bob 12-band asosida lotin izoh",
            "explanation_uz_cyrl": "ЙҲҚ 3-боб 12-банд асосида кирилл изоҳ",
            "explanation_ru": "Пояснение на русском по ПДД п. 12",
            "legal_verification_status": "VERIFIED_PRIMARY_LAW",
            "legal_doc_title": "VMQ 172 (YHQ)",
            "legal_chapter": "3-bob",
            "legal_clause": "12-band",
            "legal_doc_url": "https://lex.uz/docs/5963102",
        },
        admin_username="QA_Admin",
    )
    cq_id = res["canonical_id"]

    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        cq = conn.execute("SELECT * FROM canonical_questions WHERE canonical_id = ?", (cq_id,)).fetchone()
        assert cq["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"
        assert cq["legal_doc_title"] == "VMQ 172 (YHQ)"
        assert cq["legal_chapter"] == "3-bob"
        assert cq["legal_clause"] == "12-band"

        trs = {
            r["language"]: r["explanation"]
            for r in conn.execute("SELECT language, explanation FROM canonical_translations WHERE canonical_id = ?", (cq_id,)).fetchall()
        }
        assert trs["uz_latn"].endswith("lotin izoh")
        assert trs["uz_cyrl"].endswith("кирилл изоҳ")
        assert trs["ru"].startswith("Пояснение")
        assert get_db_catalog_revision(conn) == rev_before + 1


def test_editorial_queue_flag_filter_and_trilingual_fix(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)

    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        audit_and_seed_provenance(conn, admin_actor="phase2_test")
        filtered = list_editorial_queue(conn, status="PENDING_EDITORIAL_REVIEW", issue_flag="LANGUAGE_BLEED_UZ_IN_RU", limit=5)
        assert filtered["total"] >= 1
        assert filtered["status_counts"]["PENDING_EDITORIAL_REVIEW"] >= filtered["total"]
        first = filtered["items"][0]
        assert "uz_latn" in first["translations"]
        assert "ru" in first["translations"]

        rev_before = get_db_catalog_revision(conn)
        approve_editorial_item(
            conn,
            queue_id=first["id"],
            reviewer="Editor_Anvar",
            legal_verification_status="VERIFIED_PRIMARY_LAW",
            legal_doc_title="VMQ 172",
            legal_chapter="5-bob",
            legal_clause="31-band",
            explanations_by_lang={
                "uz_latn": "Tuzatilgan lotin izoh",
                "uz_cyrl": "Тузатилган кирилл изоҳ",
                "ru": "Исправленное русское объяснение",
            },
            question_texts_by_lang={
                "ru": "Исправленный вопрос на русском языке?",
            },
        )
        ru_row = conn.execute(
            "SELECT question_text, explanation FROM canonical_translations WHERE canonical_id = ? AND language = 'ru'",
            (first["canonical_id"],),
        ).fetchone()
        assert ru_row["question_text"] == "Исправленный вопрос на русском языке?"
        assert ru_row["explanation"] == "Исправленное русское объяснение"
        assert get_db_catalog_revision(conn) == rev_before + 1


def test_sync_webhook_fail_closed_and_editorial_admin_api(tmp_path, monkeypatch):
    import src.admin.auth_service as admin_auth
    import src.admin.routes_admin_questions as raq
    from src.db_adapter import get_db_connection

    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    client = TestClient(app)

    # 1. Fail-closed webhook when secret is unset
    monkeypatch.delenv("SYNC_WEBHOOK_SECRET", raising=False)
    res_unconfigured = client.post("/api/admin/questions/sync/webhook")
    assert res_unconfigured.status_code == 503

    # 2. Invalid secret returns 403
    monkeypatch.setenv("SYNC_WEBHOOK_SECRET", "phase2-webhook-secret")
    res_bad = client.post("/api/admin/questions/sync/webhook", headers={"X-Sync-Secret": "wrong-secret"})
    assert res_bad.status_code == 403

    # 3. Valid secret invokes sync check cleanly
    with patch.object(raq.sync_service, "check_for_updates", return_value={"has_updates": False, "newly_staged_count": 0}):
        res_ok = client.post("/api/admin/questions/sync/webhook", headers={"X-Sync-Secret": "phase2-webhook-secret"})
        assert res_ok.status_code == 200
        assert res_ok.json()["success"] is True

    # 4. Editorial queue filtering API on isolated DB
    db_file = _make_isolated_db(tmp_path)
    token = generate_session_token()
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        audit_and_seed_provenance(conn, admin_actor="phase2_api")
        admin_id = conn.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'").fetchone()[0]
        conn.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', datetime('now'), datetime('now', '+2 hours'), 0, datetime('now'))
            """,
            (token, admin_id),
        )
        conn.commit()

    monkeypatch.setattr(admin_auth, "DB_PATH", str(db_file))
    monkeypatch.setattr(raq.sync_service, "db_path", str(db_file))

    res_list = client.get(
        "/api/admin/questions/editorial?status=PENDING_EDITORIAL_REVIEW&issue_flag=LANGUAGE_BLEED_UZ_IN_RU&limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    body = res_list.json()
    assert body["success"] is True
    assert body["total"] >= 1
    assert "status_counts" in body


def test_async_fastapi_routes_never_call_sync_db_directly():
    """R-07 regression guard: every async def in src/admin and src/api calling DB helpers must use asyncio.to_thread."""
    flagged = []
    for path in sorted(glob.glob("src/admin/*.py") + glob.glob("src/api/*.py")):
        src = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                seg = ast.get_source_segment(src, node) or ""
                has_db = any(
                    k in seg
                    for k in (
                        "_get_connection(",
                        "get_db_connection(",
                        "expire_stale_orders(",
                        "get_user_active_order(",
                        "get_order_by_id(",
                        "sync_service.",
                    )
                )
                if has_db and "to_thread" not in seg:
                    flagged.append(f"{path}:{node.lineno} async def {node.name}")
    assert flagged == [], f"Blocking sync DB calls detected in async handlers: {flagged}"
