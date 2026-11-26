"""
Unit and Integration Tests for Automated Question Synchronization Engine.
"""
import pytest
import sqlite3
import os
from fastapi.testclient import TestClient

from src.api.main import app
from src.sync.adapters import YesPravaAdapter, ProPDDAdapter, BaseSourceAdapter
from src.sync.diff_detector import DiffDetector
from src.sync.incremental_unifier import IncrementalUnifier
from src.sync.service import QuestionSyncService
import uuid
from datetime import datetime, timedelta
from src.security.crypto import generate_session_token

client = TestClient(app)

@pytest.fixture
def admin_token():
    token = generate_session_token()
    now_str = datetime.utcnow().isoformat()
    exp_str = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    with sqlite3.connect("master_database.sqlite") as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'")
        row = c.fetchone()
        admin_id = row[0] if row else 1
        c.execute("""
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', ?, ?, 0, ?)
        """, (token, admin_id, now_str, exp_str, now_str))
        conn.commit()
    return token

def test_yesprava_adapter_initialization():
    adapter = YesPravaAdapter()
    assert adapter.source_code == "yesprava"
    assert adapter.base_url == "https://yesprava.uz"
    bid = adapter.resolve_build_id()
    assert bid is not None and len(bid) > 5

def test_propdd_adapter_initialization():
    adapter = ProPDDAdapter()
    assert adapter.source_code == "propdd"
    assert adapter.base_url == "https://propdd.uz"
    tickets = adapter.discover_tickets()
    assert len(tickets) >= 60

def test_diff_detector_hash_deterministic():
    text = "Yo'l belgisiga rioya qilish shartmi?"
    options = ["Ha", "Yo'q", "Faqat sutkaning qorong'i vaqtida"]
    h1 = DiffDetector.compute_canonical_hash("uz_latn", text, options)
    h2 = DiffDetector.compute_canonical_hash("uz_latn", text, options)
    assert h1 == h2
    assert len(h1) == 64

def test_incremental_unifier_canonical_sequence():
    unifier = IncrementalUnifier("master_database.sqlite")
    conn = sqlite3.connect("master_database.sqlite")
    next_int = unifier._get_next_canonical_int(conn)
    conn.close()
    assert next_int >= 1296

def test_question_sync_service_metrics():
    service = QuestionSyncService("master_database.sqlite")
    metrics = service.get_database_metrics()
    assert metrics["canonical_questions"] >= 1295
    assert metrics["canonical_translations"] >= 3885
    assert metrics["total_images"] >= 1400

def test_admin_sync_status_endpoint(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/admin/questions/sync/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "database" in data
    assert "sources" in data
    assert data["database"]["canonical_questions"] >= 1295
    assert len(data["sources"]) >= 2

def test_admin_sync_check_endpoint(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/admin/questions/sync/check", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "has_updates" in data
    assert "total_new_questions" in data
    assert "source_reports" in data

def test_staging_lifecycle_and_moderation(admin_token):
    """
    Tests full Human-in-the-Loop staging lifecycle:
    1. Quarantine question in staged_questions
    2. Admin views pending staged questions
    3. Admin edits and approves question
    4. Production canonical database receives CQ ID atomically
    5. Clean up test records
    """
    import json
    headers = {"Authorization": f"Bearer {admin_token}"}
    test_slot = 99999
    
    # 1. Insert mock staged question
    with sqlite3.connect("master_database.sqlite") as conn:
        cur = conn.cursor()
        prev_cat_ver_row = cur.execute("SELECT value FROM system_settings WHERE key = 'catalog_version'").fetchone()
        prev_cat_ver = prev_cat_ver_row[0] if prev_cat_ver_row else None
        cur.execute("""
            INSERT INTO staged_questions (
                source_code, source_ticket, source_position, change_type,
                category_slug, category_name,
                text_uz_latn, text_uz_cyrl, text_ru,
                options_json, correct_option_key, explanation,
                review_status, created_at, updated_at
            ) VALUES (
                'test_source', ?, 1, 'NEW_QUESTION',
                'umumiy-qoidalar', 'Umumiy qoidalar',
                'Test savol matni lotincha?', 'Тест савол матни кириллча?', 'Тестовый вопрос на русском?',
                ?, 'B', 'Test izohi',
                'PENDING_REVIEW', datetime('now'), datetime('now')
            );
        """, (test_slot, json.dumps([
            {"key": "A", "is_correct": False, "text_uz_latn": "A varianti", "text_uz_cyrl": "A вариант", "text_ru": "Вариант A"},
            {"key": "B", "is_correct": True, "text_uz_latn": "B varianti", "text_uz_cyrl": "B вариант", "text_ru": "Вариант B"}
        ])))
        staged_id = cur.lastrowid
        conn.commit()

    try:
        # 2. Admin retrieves staging queue
        res_list = client.get("/api/admin/questions/staging", headers=headers)
        assert res_list.status_code == 200
        data_list = res_list.json()
        assert data_list["success"] is True
        assert any(q["id"] == staged_id for q in data_list["questions"])

        # 3. Admin edits and approves question
        edit_payload = {
            "text_uz_latn": "Tahrirlangan test savol matni?",
            "text_uz_cyrl": "Таҳрирланган тест савол матни?",
            "text_ru": "Отредактированный тестовый вопрос?",
            "correct_option_key": "B",
            "explanation": "Yangi YHQ bandi bo'yicha izoh"
        }
        res_edit = client.post(f"/api/admin/questions/staging/{staged_id}/edit", json=edit_payload, headers=headers)
        assert res_edit.status_code == 200
        edit_data = res_edit.json()
        assert edit_data["success"] is True
        created_cq_id = edit_data["canonical_id"]
        assert created_cq_id.startswith("CQ-")

        # 4. Verify canonical database has the approved question
        with sqlite3.connect("master_database.sqlite") as conn:
            cur = conn.cursor()
            cur.execute("SELECT review_status, published_canonical_id FROM staged_questions WHERE id = ?", (staged_id,))
            staged_row = cur.fetchone()
            assert staged_row[0] == "APPROVED"
            assert staged_row[1] == created_cq_id

            cur.execute("SELECT canonical_id FROM canonical_questions WHERE canonical_id = ?", (created_cq_id,))
            assert cur.fetchone() is not None
            
            cur.execute("SELECT question_text FROM canonical_translations WHERE canonical_id = ? AND language = 'uz_latn'", (created_cq_id,))
            trans_row = cur.fetchone()
            assert trans_row is not None
            assert trans_row[0] == "Tahrirlangan test savol matni?"

    finally:
        # Clean up test artifacts from master DB
        with sqlite3.connect("master_database.sqlite") as conn:
            cur = conn.cursor()
            cur.execute("SELECT published_canonical_id FROM staged_questions WHERE id = ?", (staged_id,))
            row = cur.fetchone()
            if row and row[0]:
                cid = row[0]
                cur.execute("DELETE FROM audit_merge_log WHERE canonical_id = ?", (cid,))
                cur.execute("DELETE FROM question_sources WHERE question_id = ?", (cid,))
                cur.execute("DELETE FROM canonical_answers WHERE canonical_id = ?", (cid,))
                cur.execute("DELETE FROM canonical_translations WHERE canonical_id = ?", (cid,))
                cur.execute("DELETE FROM canonical_questions WHERE canonical_id = ?", (cid,))
                cur.execute("DELETE FROM questions WHERE id = ?", (cid,))
            cur.execute("DELETE FROM staged_questions WHERE id = ?", (staged_id,))
            if prev_cat_ver is None:
                cur.execute("DELETE FROM system_settings WHERE key = 'catalog_version'")
            else:
                cur.execute("UPDATE system_settings SET value = ? WHERE key = 'catalog_version'", (prev_cat_ver,))
            conn.commit()
        from src.api.routes_theory import invalidate_theory_caches
        invalidate_theory_caches(reload_engine=True)

def test_staging_rejection(admin_token):
    """
    Tests that rejecting a staged question prevents it from entering canonical database.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    with sqlite3.connect("master_database.sqlite") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staged_questions (
                source_code, source_ticket, source_position, change_type,
                category_slug, category_name,
                text_uz_latn, text_uz_cyrl, text_ru,
                options_json, correct_option_key, explanation,
                review_status, created_at, updated_at
            ) VALUES (
                'test_source', 99998, 1, 'NEW_QUESTION',
                'umumiy-qoidalar', 'Umumiy qoidalar',
                'Rad etilishi kerak boʻlgan savol?', 'Рад этилиши керак бўлган савол?', 'Вопрос для отклонения?',
                '[]', 'A', 'Izoh',
                'PENDING_REVIEW', datetime('now'), datetime('now')
            );
        """, ())
        staged_id = cur.lastrowid
        conn.commit()

    try:
        reject_res = client.post(
            f"/api/admin/questions/staging/{staged_id}/reject",
            json={"reason": "Format talabiga mos emas"},
            headers=headers
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["success"] is True

        with sqlite3.connect("master_database.sqlite") as conn:
            cur = conn.cursor()
            cur.execute("SELECT review_status, reviewer_notes FROM staged_questions WHERE id = ?", (staged_id,))
            row = cur.fetchone()
            assert row[0] == "REJECTED"
            assert row[1] == "Format talabiga mos emas"
    finally:
        with sqlite3.connect("master_database.sqlite") as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM staged_questions WHERE id = ?", (staged_id,))
            conn.commit()

