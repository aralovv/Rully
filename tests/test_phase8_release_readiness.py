"""
RULLY 2.0 Phase 8 Release Readiness, Rollback Drill & Staging E2E Sign-Off Suite:
- Reversible Migration Rollback & Forward Re-Apply Drill (003 -> 001/002 -> 003) on isolated tmp_path SQLite
- Canonical Bundle SHA-256 Parity & Sanitized Export Drill (U-07 zero-secret scrub)
- Semantic 401 Protection Matrix vs 200 Public / 503-403 Webhook Fail-Closed Contracts
- End-to-End Staging Student (Auth -> Quiz -> SM-2 -> Analytics) + Admin Observability Smoke Journey
"""

import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.security import generate_dev_init_data
from src.bot.database import BotDatabase
from src.db.catalog_bundle import get_db_catalog_revision, verify_and_load_canonical_bundle
from src.db.migrations_v2 import (
    apply_all_migrations,
    rollback_phase1_migrations_local_test,
    rollback_phase5_migrations_local_test,
    verify_phase5_schema_parity,
    verify_schema_parity,
)
from src.db.sanitized_export import export_sanitized_dev_sqlite
from src.security.crypto import generate_session_token

MASTER_DB = Path("master_database.sqlite")


def _make_isolated_db(tmp_path: Path, name: str = "phase8_staging.sqlite") -> Path:
    db_file = tmp_path / name
    shutil.copy2(MASTER_DB, db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    apply_all_migrations(conn)
    conn.close()
    return db_file


def test_phase8_full_rollback_and_reapply_drill(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path, "rollback_drill.sqlite")

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        assert verify_schema_parity(conn)["passed"] is True
        assert verify_phase5_schema_parity(conn)["passed"] is True
        q_before = conn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0]
        assert q_before == 1327

        # Step 1: Rollback Phase 5 (003_phase5_user_question_srs)
        rb5 = rollback_phase5_migrations_local_test(conn)
        assert rb5["rolled_back"] is True
        assert verify_phase5_schema_parity(conn)["passed"] is False
        assert conn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0] == 1327

        # Step 2: Rollback Phase 1-2 governance/editorial/provenance migrations
        rb1 = rollback_phase1_migrations_local_test(conn)
        assert rb1["rolled_back"] is True
        assert verify_schema_parity(conn)["passed"] is False
        assert conn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0] == 1327

        # Step 3: Forward recovery restores 100% schema parity cleanly
        apply_all_migrations(conn)
        assert verify_schema_parity(conn)["passed"] is True
        assert verify_phase5_schema_parity(conn)["passed"] is True
        assert conn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0] == 1327
    finally:
        conn.close()


def test_phase8_canonical_bundle_and_sanitized_export_drill(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    bundle_data, err = verify_and_load_canonical_bundle("data/canonical_bundle.json")
    assert err is None
    assert bundle_data is not None
    assert bundle_data["canonical_count"] == 1327
    assert bundle_data["schema_version"] == 2

    db_file = _make_isolated_db(tmp_path, "export_src.sqlite")
    export_target = tmp_path / "sanitized_dev.sqlite"
    with sqlite3.connect(str(db_file)) as src_conn:
        src_conn.row_factory = sqlite3.Row
        assert get_db_catalog_revision(src_conn) is not None
        src_conn.execute(
            """
            INSERT OR REPLACE INTO mtproto_accounts (id, phone_number, session_encrypted, tg_username, connection_status, created_at, updated_at)
            VALUES (1, '+998901234567', 'SENSITIVE_LIVE_SESSION', 'live_ops', 'CONNECTED', datetime('now'), datetime('now'))
            """
        )
        src_conn.commit()
        res = export_sanitized_dev_sqlite(src_conn, str(export_target))
        assert res["status"] == "SANITIZED_DEV_DB_CREATED"
        assert res["integrity_check"] == "ok"
        assert res["copied_counts"]["canonical_questions"] == 1327

    with sqlite3.connect(str(export_target)) as dst_conn:
        assert dst_conn.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0] == 1327
        sess_val = dst_conn.execute("SELECT session_encrypted FROM mtproto_accounts WHERE id = 1").fetchone()
        assert sess_val is None or sess_val[0] in ("", None)


def test_phase8_semantic_401_and_e2e_staging_smoke_journey(tmp_path, monkeypatch):
    import src.admin.auth_service as admin_auth
    import src.admin.routes_admin_logs as ral
    import src.api.deps as deps
    from src.api.routes_auth import _AUTH_BUNDLE_CACHE

    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SYNC_WEBHOOK_SECRET", raising=False)

    db_file = _make_isolated_db(tmp_path, "staging_e2e.sqlite")
    iso_db = BotDatabase(str(db_file))

    def _iso_conn():
        c = sqlite3.connect(str(db_file))
        c.row_factory = sqlite3.Row
        return c

    deps._user_cache.clear()
    _AUTH_BUNDLE_CACHE.clear()
    app.dependency_overrides[deps.get_db] = lambda: iso_db
    monkeypatch.setattr(admin_auth, "DB_PATH", str(db_file))
    monkeypatch.setattr(ral, "DB_PATH", str(db_file))
    monkeypatch.setattr(ral, "_get_connection", _iso_conn)

    client = TestClient(app)

    try:
        # 1. Public shell & health checks -> 200 + Phase 7 hardening headers
        for pub in ("/", "/admin/", "/api/health", "/api/ping"):
            r = client.get(pub)
            assert r.status_code == 200, f"{pub} failed: {r.status_code}"
            assert r.headers.get("X-Content-Type-Options") == "nosniff"
            assert r.headers.get("X-Request-ID")

        # 2. Protected routes must fail closed with semantic 401 (never 500 or 200)
        for priv_get in (
            "/api/user/me",
            "/api/categories?lang=uz_latn",
            "/api/tickets?lang=uz_latn",
            "/api/srs/queue?lang=uz_latn",
            "/api/admin/system/health",
            "/api/admin/system/metrics",
            "/api/admin/payments/health",
        ):
            r = client.get(priv_get)
            assert r.status_code == 401, f"{priv_get} expected 401, got {r.status_code}"

        assert client.post("/api/ai/chat", json={"message": "Salom"}).status_code == 401
        assert client.post("/api/admin/questions/sync/webhook").status_code == 503

        # 3. Full E2E Student Journey (Auth -> Tickets -> Start Ticket -> Answer -> SM-2)
        uid = 990801
        dev_init = generate_dev_init_data(user_id=uid)
        auth_res = client.post("/api/auth/telegram", json={"init_data": dev_init})
        assert auth_res.status_code == 200
        headers = {"X-Telegram-Init-Data": dev_init}

        tickets_res = client.get("/api/tickets?lang=uz_latn", headers=headers)
        assert tickets_res.status_code == 200
        assert tickets_res.json()["total_tickets"] == 67

        start_res = client.post(
            "/api/session/start",
            json={"session_type": "BILET", "ticket_number": 1, "language": "uz_latn"},
            headers=headers,
        )
        assert start_res.status_code == 200
        sess_payload = start_res.json()
        q0 = sess_payload["questions"][0]

        ans_res = client.post(
            "/api/session/answer",
            json={
                "session_id": sess_payload["session_id"],
                "canonical_id": q0["canonical_id"],
                "selected_key": "A",
                "response_time_ms": 2800,
            },
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert "srs" in ans_res.json()

        srs_res = client.get("/api/srs/queue?lang=uz_latn", headers=headers)
        assert srs_res.status_code == 200
        assert srs_res.json()["summary"]["tracked_count"] >= 1

        # 4. Admin Observability & Reconciliation Check
        admin_tok = generate_session_token()
        with _iso_conn() as conn:
            admin_id = conn.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'").fetchone()[0]
            conn.execute(
                """
                INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
                VALUES (?, ?, '127.0.0.1', 'pytest', datetime('now'), datetime('now', '+2 hours'), 0, datetime('now'))
                """,
                (admin_tok, admin_id),
            )
            conn.commit()

        adm_headers = {"Authorization": f"Bearer {admin_tok}"}
        m_res = client.get("/api/admin/system/metrics", headers=adm_headers)
        assert m_res.status_code == 200
        assert m_res.json()["metrics"]["total_requests"] >= 5

        h_res = client.get("/api/admin/system/health", headers=adm_headers)
        assert h_res.status_code == 200
        assert h_res.json()["overall_status"] == "HEALTHY"
    finally:
        app.dependency_overrides.pop(deps.get_db, None)
        deps._user_cache.clear()
        _AUTH_BUNDLE_CACHE.clear()
