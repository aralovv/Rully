"""
Wave 4 Admin Panel Security (CSP, RBAC, CSRF), Zero-PII Static UI,
Payment Reconciliation, Editorial Bulk-Approve & AI Draft Regression Suite.
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import secrets
import subprocess
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app
from src.db_adapter import get_db_connection
from src.security.crypto import hash_password


ROOT_DIR = Path(__file__).resolve().parent.parent


def _create_admin_with_session(username: str, role: str) -> str:
    db_path = os.getenv("DB_PATH", "master_database.sqlite")
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    exp_str = (now_dt + timedelta(hours=2)).isoformat()
    token = f"adm_sess_{role.lower()}_{secrets.token_hex(8)}"

    with get_db_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM admin_users WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            admin_id = row[0] if not hasattr(row, "keys") else row["id"]
            c.execute("UPDATE admin_users SET role = ?, is_active = 1 WHERE id = ?", (role, admin_id))
        else:
            c.execute(
                """
                INSERT INTO admin_users (username, password_hash, telegram_id, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (username, hash_password("TestAdminPw123!"), 700001, role, now_str),
            )
            admin_id = c.lastrowid
        c.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', ?, ?, 0, ?)
            """,
            (token, admin_id, now_str, exp_str, now_str),
        )
        conn.commit()
    return token


def test_admin_csp_strict_no_unsafe_inline_and_clean_html():
    client = TestClient(app)
    res = client.get("/admin")
    assert res.status_code == 200
    csp = res.headers.get("Content-Security-Policy", "")
    # script-src must NOT contain 'unsafe-inline'
    script_src_match = re.search(r"script-src\s+([^;]+)", csp)
    assert script_src_match is not None
    assert "'unsafe-inline'" not in script_src_match.group(1)

    html = (ROOT_DIR / "static" / "admin" / "index.html").read_text(encoding="utf-8")
    # Zero inline JS attributes
    assert not re.search(r"\bon(click|change|input|submit)\s*=", html, re.IGNORECASE)
    # Zero hardcoded founder PII
    for pii in ("Anvarjon", "***9701", "ANVARJON ARALOV", "9860 **** **** 5370"):
        assert pii not in html
    # Observability accordion fixed from accordion-body -> accordion-content
    assert "accordion-body" not in html
    assert "acc-observability" in html

    admin_js = (ROOT_DIR / "static" / "admin" / "admin.js").read_text(encoding="utf-8")
    for pii in ("Anvarjon", "***9701"):
        assert pii not in admin_js
    assert not re.search(r"\bon(click|change|input)\s*=", admin_js, re.IGNORECASE)

    chk = subprocess.run(["node", "--check", "static/admin/admin.js"], cwd=str(ROOT_DIR), capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr


def test_admin_rbac_enforced_across_roles():
    client = TestClient(app)
    mod_tok = _create_admin_with_session("wave4_mod", "MODERATOR")
    fin_tok = _create_admin_with_session("wave4_fin", "FINANCE")
    sup_tok = _create_admin_with_session("wave4_sup", "SUPERADMIN")

    mod_headers = {"X-Admin-Session": mod_tok}
    fin_headers = {"X-Admin-Session": fin_tok}
    sup_headers = {"X-Admin-Session": sup_tok}

    # MODERATOR can access editorial, but blocked from finance, analytics, users, and system
    assert client.get("/api/admin/questions/editorial?limit=5", headers=mod_headers).status_code == 200
    assert client.get("/api/admin/payments/reconciliation", headers=mod_headers).status_code == 403
    assert client.get("/api/admin/analytics/activity", headers=mod_headers).status_code == 403
    assert client.get("/api/admin/users", headers=mod_headers).status_code == 403
    assert client.get("/api/admin/system/health", headers=mod_headers).status_code == 403

    # FINANCE can access payments reconciliation, unmatched status filter, analytics, and users (?query alias), but blocked from SUPERADMIN system logs
    assert client.get("/api/admin/payments/reconciliation", headers=fin_headers).status_code == 200
    assert client.get("/api/admin/payments/unmatched?status=UNRESOLVED", headers=fin_headers).status_code == 200
    assert client.get("/api/admin/analytics/activity", headers=fin_headers).status_code == 200
    assert client.get("/api/admin/users?query=test", headers=fin_headers).status_code == 200
    assert client.get("/api/admin/system/audit-logs", headers=fin_headers).status_code == 403
    assert client.get("/api/admin/system/health", headers=fin_headers).status_code == 403

    # SUPERADMIN has global access
    assert client.get("/api/admin/system/health", headers=sup_headers).status_code == 200
    assert client.get("/api/admin/system/audit-logs?limit=5", headers=sup_headers).status_code == 200
    assert client.get("/api/admin/payments/reconciliation", headers=sup_headers).status_code == 200


def test_editorial_enriched_queue_ai_draft_and_bulk_approve():
    client = TestClient(app)
    mod_tok = _create_admin_with_session("wave4_mod2", "MODERATOR")
    headers = {"X-Admin-Session": mod_tok}

    # Fetch pending editorial queue and confirm enriched fields exist
    res = client.get("/api/admin/questions/editorial?status=PENDING_EDITORIAL_REVIEW&limit=3", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    first_item = items[0]
    assert "image_url" in first_item
    assert "options" in first_item
    assert "correct_option_key" in first_item
    qid = first_item["id"]

    # AI Draft endpoint (mocked Gemini response) quarantines draft without overwriting canonical table directly
    mock_gemini_resp = (
        {"candidates": [{"content": {"parts": [{"text": '{"uz_latn":"Test lotin izoh","uz_cyrl":"Тест кирилл изоҳ","ru":"Тестовое пояснение"}'}]}}]},
        200,
        None,
    )
    with patch("src.ai.gemini_service.GeminiService._call_gemini_with_fallback", new=AsyncMock(return_value=mock_gemini_resp)), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
        draft_res = client.post(f"/api/admin/questions/editorial/{qid}/ai-draft", headers=headers)
        assert draft_res.status_code == 200, draft_res.text
        d_json = draft_res.json()
        assert d_json["success"] is True
        assert d_json["drafts"]["uz_latn"] == "Test lotin izoh"

    # Bulk approve works cleanly
    bulk_res = client.post(
        "/api/admin/questions/editorial/bulk-approve",
        json={
            "queue_ids": [qid],
            "legal_verification_status": "VERIFIED_PRIMARY_LAW",
            "legal_doc_title": "VMQ 172",
            "legal_clause": "19-band",
            "reviewer_notes": "Wave4 test bulk approve",
        },
        headers=headers,
    )
    assert bulk_res.status_code == 200, bulk_res.text
    assert first_item["canonical_id"] in bulk_res.json()["approved"]


def test_review_approve_accepts_note_and_notes_aliases():
    from src.admin.routes_admin_payments import ResolveReviewRequest

    assert ResolveReviewRequest(note="legacy ok").resolved_notes() == "legacy ok"
    assert ResolveReviewRequest(notes="modern ok").resolved_notes() == "modern ok"
