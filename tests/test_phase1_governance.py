"""
Phase 1 Governance, Archive Isolation, Schema Migration Parity,
Classified Provenance, Editorial Quarantine, and Sanitized Export Tests.

All tests execute strictly against isolated temporary databases in tmp_path.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.bot.database import BotDatabase
from src.db.archive_tier0 import (
    TIER0_TABLES,
    extract_tier0_sqlite_file,
    rollback_tier0_from_archive,
    verify_tier0_isolation_sqlite,
)
from src.db.migrations_v2 import (
    apply_phase1_migrations,
    rollback_phase1_migrations_local_test,
    verify_schema_parity,
)
from src.db.provenance_classifier import (
    approve_editorial_item,
    audit_and_seed_provenance,
    list_editorial_queue,
    submit_ai_draft,
)
from src.db.sanitized_export import WIPED_TABLES, export_sanitized_dev_sqlite
from src.db.sqlite_utils import backup_sqlite_wal_safe, list_user_tables
from src.db_adapter import execute_batch
from src.security.crypto import generate_session_token
from src.sync.staging_manager import StagingManager


def _make_isolated_copy(tmp_path, name: str = "isolated.sqlite") -> str:
    dst = str(tmp_path / name)
    backup_sqlite_wal_safe("master_database.sqlite", dst, allow_overwrite=True)
    return dst


def test_tier0_isolation_extract_and_rollback(tmp_path):
    runtime_db = _make_isolated_copy(tmp_path, "tier0_runtime.sqlite")
    archive_db = str(tmp_path / "tier0_archive.sqlite")
    real_tier0_archive = os.path.join("data", "archive", "rully_tier0_archive.sqlite")

    conn = sqlite3.connect(runtime_db)
    # After Phase 1F, local master DB already has Tier 0 extracted; verify idempotency and hydrate copy from archive if needed
    iso_initial = verify_tier0_isolation_sqlite(conn)
    assert iso_initial["isolated"] is True
    if not iso_initial["present_tables"]:
        already = extract_tier0_sqlite_file(runtime_db, archive_db, drop_from_runtime=True, dry_run=False)
        assert already["status"] == "ALREADY_ARCHIVED"
        assert os.path.exists(real_tier0_archive), "Expected Phase 1F archive at data/archive/rully_tier0_archive.sqlite"
        rb_pre = rollback_tier0_from_archive(conn, real_tier0_archive)
        assert rb_pre["status"] == "ROLLED_BACK"

    iso = verify_tier0_isolation_sqlite(conn)
    assert iso["isolated"] is True
    assert set(iso["present_tables"]) == set(TIER0_TABLES)
    conn.close()

    # Extract and drop ONLY Tier 0 tables
    res = extract_tier0_sqlite_file(runtime_db, archive_db, drop_from_runtime=True, dry_run=False)
    assert res["status"] == "ARCHIVED_AND_VERIFIED"
    assert res["dropped"] is True
    assert res["post_drop_integrity_check"] == [("ok",)]
    assert res["post_drop_foreign_key_check"] == []
    assert res["tables"]["archived_duplicate_source_traces"]["row_count"] == 306
    assert res["tables"]["proposed_source_trace_cleanup"]["row_count"] == 306

    # Confirm active ETL & runtime tables remain intact per Decision U-01
    r_conn = sqlite3.connect(runtime_db)
    tables_after = set(list_user_tables(r_conn))
    assert "archived_duplicate_source_traces" not in tables_after
    assert "proposed_source_trace_cleanup" not in tables_after
    for protected in (
        "questions",
        "answers",
        "verification_records",
        "question_sources",
        "sources",
        "audit_merge_log",
        "staged_questions",
        "canonical_questions",
    ):
        assert protected in tables_after

    assert r_conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 5977
    assert r_conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 19579
    assert r_conn.execute("SELECT COUNT(*) FROM verification_records").fetchone()[0] == 5945

    # Test rollback restores exact counts and hashes
    rb = rollback_tier0_from_archive(r_conn, archive_db)
    assert rb["status"] == "ROLLED_BACK"
    assert set(rb["restored"].keys()) == set(TIER0_TABLES)
    assert r_conn.execute("SELECT COUNT(*) FROM archived_duplicate_source_traces").fetchone()[0] == 306
    assert r_conn.execute("SELECT COUNT(*) FROM proposed_source_trace_cleanup").fetchone()[0] == 306
    r_conn.close()


def test_migration_001_002_turso_gap_simulation_and_rollback(tmp_path):
    sim_db = _make_isolated_copy(tmp_path, "turso_sim.sqlite")
    conn = sqlite3.connect(sim_db)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Simulate exact Production Turso pre-Phase-1D state (no user_ticket_progress, no session_answers.user_id, missing 6 indexes)
    conn.execute("DROP TABLE IF EXISTS user_ticket_progress;")
    for idx in (
        "idx_answers_session",
        "idx_exam_results_user",
        "idx_session_answers_user_canon",
        "idx_session_answers_user_recent",
        "idx_sessions_user_status",
        "idx_ticket_progress_user",
    ):
        conn.execute(f"DROP INDEX IF EXISTS {idx};")

    # Recreate session_answers without user_id + seed a session and answer row
    conn.execute("DELETE FROM session_answers;")
    conn.execute("ALTER TABLE session_answers DROP COLUMN user_id;")
    now_ts = datetime.utcnow().isoformat()
    uid = 8809526955
    conn.execute(
        "INSERT OR IGNORE INTO telegram_users (user_id, username, language, created_at, last_active_at) VALUES (?, 'sim', 'uz_latn', ?, ?)",
        (uid, now_ts, now_ts),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO user_sessions (
            session_id, user_id, session_type, language, total_questions,
            start_time, question_ids_json, created_at, updated_at
        ) VALUES ('SIM-SESS-1', ?, 'EXAM', 'uz_latn', 20, 1000.0, '["CANON-YHQ-0001"]', ?, ?)
        """,
        (uid, now_ts, now_ts),
    )
    conn.execute(
        """
        INSERT INTO session_answers (session_id, canonical_id, selected_key, correct_key, is_correct, answered_at)
        VALUES ('SIM-SESS-1', 'CANON-YHQ-0001', 'A', 'A', 1, ?)
        """,
        (now_ts,),
    )
    conn.commit()

    # Apply Phase 1 migrations twice to prove idempotency
    res1 = apply_phase1_migrations(conn)
    res2 = apply_phase1_migrations(conn)
    assert res1["parity"]["passed"] is True
    assert res2["parity"]["passed"] is True

    # Confirm session_answers.user_id backfilled accurately from user_sessions
    backfilled_uid = conn.execute(
        "SELECT user_id FROM session_answers WHERE session_id = 'SIM-SESS-1'"
    ).fetchone()[0]
    assert backfilled_uid == uid

    # Confirm integrity & FK constraints pass
    assert conn.execute("PRAGMA integrity_check;").fetchone() == ("ok",)
    assert conn.execute("PRAGMA foreign_key_check;").fetchall() == []

    # Verify BotDatabase session answer submission & ticket progress succeed cleanly after migration
    BotDatabase._ticket_schema_ready = False
    bot_db = BotDatabase(sim_db)
    ans_res = bot_db.process_session_answer("SIM-SESS-1", uid, "CANON-YHQ-0002", "B", "B", True, "EXAM")
    assert ans_res["is_new"] is True
    bot_db.upsert_ticket_progress(uid, 1, 20, 19, 95.0, True, "SIM-SESS-1")
    prog = bot_db.get_ticket_progress_map(uid)
    assert prog[1]["is_passed"] is True

    # Test isolated schema rollback
    rb = rollback_phase1_migrations_local_test(conn)
    assert rb["rolled_back"] is True
    assert "user_ticket_progress" not in rb["tables_remaining"]
    conn.close()


def test_execute_batch_atomicity_and_staging_no_fake_law(tmp_path):
    db_path = _make_isolated_copy(tmp_path, "staging_test.sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_phase1_migrations(conn)

    # Atomic batch rollback check: 2nd statement violates UNIQUE/PK, so 1st insert must roll back
    before_cnt = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        execute_batch(conn, [
            ("INSERT INTO categories (slug, name) VALUES ('atomic-probe', 'Atomic Probe')", []),
            ("INSERT INTO categories (slug, name) VALUES ('atomic-probe', 'Duplicate Fail')", []),
        ])
    after_cnt = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert after_cnt == before_cnt

    # Insert staged item and approve via StagingManager -> must NOT claim Resolution 172 without legal_reference
    now_ts = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO staged_questions (
            source_code, source_ticket, source_position, change_type,
            category_slug, category_name, text_uz_latn, text_uz_cyrl, text_ru,
            options_json, correct_option_key, explanation, review_status, created_at, updated_at
        ) VALUES (
            'yesprava', 8888, 1, 'NEW_QUESTION',
            'umumiy-qoidalar', 'Umumiy qoidalar',
            'Staged test?', 'Стагед тест?', 'Тест?',
            ?, 'A', 'Test explanation', 'PENDING_REVIEW', ?, ?
        )
        """,
        (
            json.dumps([
                {"key": "A", "sort_order": 0, "is_correct": 1, "text_uz_latn": "Ha"},
                {"key": "B", "sort_order": 1, "is_correct": 0, "text_uz_latn": "Yoq"},
            ]),
            now_ts,
            now_ts,
        ),
    )
    staged_id = cur.lastrowid
    conn.commit()
    conn.close()

    mgr = StagingManager(db_path=db_path, backup_dir=str(tmp_path / "backups"))
    pub = mgr.approve_question(staged_id, admin_username="QA_Admin")
    assert pub["success"] is True

    c2 = sqlite3.connect(db_path)
    c2.row_factory = sqlite3.Row
    row = c2.execute(
        "SELECT legal_reference, legal_act_title, legal_verification_status FROM canonical_questions WHERE canonical_id = ?",
        (pub["canonical_id"],),
    ).fetchone()
    assert row["legal_reference"] is None
    assert row["legal_act_title"] is None
    assert row["legal_verification_status"] == "UNRESOLVED_LEGAL_REVIEW"
    c2.close()


def test_provenance_classification_and_editorial_quarantine(tmp_path):
    db_path = _make_isolated_copy(tmp_path, "editorial_test.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_phase1_migrations(conn)

    # Inject simulated RU language bleed and missing legal_reference on isolated copy to verify deterministic detectors
    conn.execute(
        """
        UPDATE canonical_translations
        SET explanation = 'Согласно пункту ПДД. (Eslatma: VMQ 318-son qaroriga asosan)'
        WHERE canonical_id = 'CANON-YHQ-0001' AND language = 'ru'
        """
    )
    conn.execute(
        """
        UPDATE canonical_questions
        SET legal_reference = '', legal_verification_status = 'UNRESOLVED_LEGAL_REVIEW', editorial_reviewed_by = NULL
        WHERE canonical_id = 'CQ-1296'
        """
    )
    conn.commit()

    audit_res = audit_and_seed_provenance(conn, admin_actor="qa_auditor")
    assert audit_res["total_canonical_evaluated"] == 1327
    cls_counts = audit_res["classification_counts"]
    assert (
        cls_counts["VERIFIED_PRIMARY_LAW"]
        + cls_counts["VERIFIED_FIRST_AID_OR_TECH"]
        + cls_counts["UNRESOLVED_LEGAL_REVIEW"]
        + cls_counts["already_verified_preserved"]
    ) == audit_res["total_canonical_evaluated"]
    assert (cls_counts["VERIFIED_PRIMARY_LAW"] + cls_counts["already_verified_preserved"]) >= 4
    assert cls_counts["UNRESOLVED_LEGAL_REVIEW"] >= 1
    assert audit_res["issue_flag_totals"].get("MISSING_LEGAL_REFERENCE", 0) >= 1
    assert audit_res["issue_flag_totals"].get("LANGUAGE_BLEED_UZ_IN_RU", 0) >= 1

    # AI-generated draft MUST stay strictly AI_DRAFT_PENDING_REVIEW and NEVER auto-touch canonical tables
    orig_expl = conn.execute(
        "SELECT explanation FROM canonical_translations WHERE canonical_id = 'CQ-1296' AND language = 'uz_latn'"
    ).fetchone()[0]
    draft_id = submit_ai_draft(
        conn,
        canonical_id="CQ-1296",
        language="uz_latn",
        draft_explanation="AI draft explanation awaiting human check",
        draft_legal_chapter="13-bob",
        draft_legal_clause="99-band",
    )
    still_orig = conn.execute(
        "SELECT explanation FROM canonical_translations WHERE canonical_id = 'CQ-1296' AND language = 'uz_latn'"
    ).fetchone()[0]
    assert still_orig == orig_expl

    q_ai = list_editorial_queue(conn, status="AI_DRAFT_PENDING_REVIEW")
    assert q_ai["total"] == 1
    assert q_ai["items"][0]["id"] == draft_id

    # Approving VERIFIED_PRIMARY_LAW without citation must fail
    with pytest.raises(ValueError):
        approve_editorial_item(
            conn,
            queue_id=draft_id,
            reviewer="Admin",
            legal_verification_status="VERIFIED_PRIMARY_LAW",
            legal_doc_title="",
            legal_chapter="",
            legal_clause="",
        )

    # Human approval with full citation publishes cleanly
    app_res = approve_editorial_item(
        conn,
        queue_id=draft_id,
        reviewer="Anvarjon",
        legal_verification_status="VERIFIED_PRIMARY_LAW",
        legal_doc_title="Vazirlar Mahkamasining 172-son qarori (YHQ)",
        legal_doc_url="https://lex.uz/docs/5963102",
        legal_chapter="13-bob",
        legal_clause="99-band",
        legal_effective_date="2022-05-01",
        approved_explanation="Tasdiqlangan inson tahriri izohi",
    )
    assert app_res["success"] is True

    cq = conn.execute(
        "SELECT legal_verification_status, legal_chapter, legal_clause, editorial_reviewed_by FROM canonical_questions WHERE canonical_id = 'CQ-1296'"
    ).fetchone()
    assert cq["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"
    assert cq["legal_chapter"] == "13-bob"
    assert cq["legal_clause"] == "99-band"
    assert cq["editorial_reviewed_by"] == "Anvarjon"

    tr = conn.execute(
        "SELECT explanation, translation_status FROM canonical_translations WHERE canonical_id = 'CQ-1296' AND language = 'uz_latn'"
    ).fetchone()
    assert tr["explanation"] == "Tasdiqlangan inson tahriri izohi"
    assert tr["translation_status"] == "ADMIN_VERIFIED"
    conn.close()


def test_sanitized_downward_export_scrubs_pii_and_secrets(tmp_path):
    prod_like_db = _make_isolated_copy(tmp_path, "prod_like.sqlite")
    pconn = sqlite3.connect(prod_like_db)
    now_ts = datetime.utcnow().isoformat()
    pconn.execute(
        "INSERT OR REPLACE INTO telegram_users (user_id, username, first_name, language, created_at, last_active_at) VALUES (7770001, 'real_customer', 'SecretName', 'ru', ?, ?)",
        (now_ts, now_ts),
    )
    pconn.execute(
        "INSERT OR REPLACE INTO mtproto_accounts (id, phone_number, session_encrypted, tg_username, connection_status, created_at, updated_at) VALUES (1, '+998901112233', 'TOP_SECRET_SESSION_STRING', 'real_acc', 'CONNECTED', ?, ?)",
        (now_ts, now_ts),
    )
    pconn.execute(
        "INSERT INTO ai_conversations (user_id, session_id, role, content, created_at) VALUES (7770001, 's1', 'user', 'PRIVATE_AI_PROMPT', ?)",
        (now_ts,),
    )
    pconn.execute(
        "INSERT OR REPLACE INTO payment_cards (id, cardholder_name, card_number_encrypted, card_number_masked, card_suffix, display_name, created_at, updated_at) VALUES (1, 'REAL OWNER', 'ENC:9860REALCARD', '9860 **** **** 9999', '9999', 'Real Card', ?, ?)",
        (now_ts, now_ts),
    )
    pconn.execute(
        "UPDATE admin_users SET password_hash = 'PROD_ARGON2_HASH_SECRET' WHERE id = 1"
    )
    pconn.commit()

    out_dev_db = str(tmp_path / "sanitized_dev.sqlite")
    res = export_sanitized_dev_sqlite(pconn, out_dev_db)
    pconn.close()
    assert res["status"] == "SANITIZED_DEV_DB_CREATED"
    assert res["integrity_check"] == "ok"
    assert res["foreign_key_check"] == "ok"

    dconn = sqlite3.connect(out_dev_db)
    assert dconn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0] == 1327
    assert dconn.execute("SELECT COUNT(*) FROM canonical_translations").fetchone()[0] == 3981
    assert "archived_duplicate_source_traces" not in list_user_tables(dconn)
    assert "proposed_source_trace_cleanup" not in list_user_tables(dconn)

    # Confirm ZERO secrets or real customer rows survived
    assert dconn.execute("SELECT COUNT(*) FROM telegram_users WHERE user_id = 7770001").fetchone()[0] == 0
    assert "TOP_SECRET_SESSION_STRING" not in (
        dconn.execute("SELECT session_encrypted FROM mtproto_accounts WHERE id = 1").fetchone()[0] or ""
    )
    assert dconn.execute("SELECT card_number_encrypted FROM payment_cards WHERE id = 1").fetchone()[0] == "ENC:9860000000005370"
    assert dconn.execute("SELECT password_hash FROM admin_users WHERE id = 1").fetchone()[0] != "PROD_ARGON2_HASH_SECRET"
    for wt in WIPED_TABLES:
        assert dconn.execute(f'SELECT COUNT(*) FROM "{wt}"').fetchone()[0] == 0
    dconn.close()


def test_editorial_api_endpoints_and_auth_gates(tmp_path, monkeypatch):
    import src.admin.routes_admin_questions as raq
    import src.admin.deps as admin_deps

    iso_db = _make_isolated_copy(tmp_path, "api_editorial.sqlite")
    conn = sqlite3.connect(iso_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    apply_phase1_migrations(conn)
    now_ts = datetime.utcnow().isoformat()
    exp_ts = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    tok = generate_session_token()
    adm_id = conn.execute("SELECT id FROM admin_users LIMIT 1").fetchone()[0]
    conn.execute(
        """
        INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
        VALUES (?, ?, '127.0.0.1', 'pytest', ?, ?, 0, ?)
        """,
        (tok, adm_id, now_ts, exp_ts, now_ts),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DB_PATH", iso_db)
    monkeypatch.setattr(raq.sync_service, "db_path", iso_db)
    monkeypatch.setattr(raq.sync_service.staging, "db_path", iso_db)
    monkeypatch.setattr(admin_deps, "validate_admin_session", lambda t: {"id": adm_id, "username": "QA_Editor", "telegram_id": 1956239701, "role": "SUPERADMIN", "session_id": t} if t == tok else None)

    client = TestClient(app)
    # 1. Semantic 401 gate without auth
    assert client.get("/api/admin/questions/editorial").status_code == 401
    assert client.get("/api/admin/auth/me").status_code == 401

    headers = {"Authorization": f"Bearer {tok}"}

    # 2. Seed audit deterministically
    seed_res = client.post("/api/admin/questions/editorial/audit-seed", headers=headers)
    assert seed_res.status_code == 200
    assert seed_res.json()["total_canonical_evaluated"] == 1327

    # 3. Quarantine AI draft -> stays strictly AI_DRAFT_PENDING_REVIEW
    draft_res = client.post(
        "/api/admin/questions/editorial/submit-ai-draft",
        headers=headers,
        json={
            "canonical_id": "CQ-1297",
            "language": "uz_latn",
            "draft_explanation": "AI proposed explanation draft",
            "draft_legal_chapter": "23-bob",
            "draft_legal_clause": "144-band",
        },
    )
    assert draft_res.status_code == 200
    qid = draft_res.json()["queue_id"]
    assert draft_res.json()["review_status"] == "AI_DRAFT_PENDING_REVIEW"

    # 4. Reject VERIFIED_PRIMARY_LAW without citation (400)
    bad_app = client.post(
        f"/api/admin/questions/editorial/{qid}/approve",
        headers=headers,
        json={"legal_verification_status": "VERIFIED_PRIMARY_LAW"},
    )
    assert bad_app.status_code == 400

    # 5. Valid human approval
    ok_app = client.post(
        f"/api/admin/questions/editorial/{qid}/approve",
        headers=headers,
        json={
            "legal_verification_status": "VERIFIED_PRIMARY_LAW",
            "legal_doc_title": "Vazirlar Mahkamasining 172-son qarori (YHQ)",
            "legal_doc_url": "https://lex.uz/docs/5963102",
            "legal_chapter": "23-bob",
            "legal_clause": "144-band",
            "approved_explanation": "Yuk tashish qoidalari bo'yicha rasmiy izoh",
        },
    )
    assert ok_app.status_code == 200
    assert ok_app.json()["legal_verification_status"] == "VERIFIED_PRIMARY_LAW"

