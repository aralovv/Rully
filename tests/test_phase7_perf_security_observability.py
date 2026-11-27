"""
RULLY 2.0 Phase 7 Verification Tests (Isolated tmp_path SQLite + TestClient + Fresh Interpreter Split Check):
- Performance / Vercel Cold-Start Router Split (create_app(public_only=True), zero eager admin imports, lazy mount & disable mode)
- Security Hardening (context-aware CSP, frame-ancestors vs X-Frame-Options, HSTS, CORS, proxy-aware get_client_ip, sanitized 500 handler)
- Full-Stack Observability (ObservabilityRegistry p50/p95, /api/admin/system/metrics, /api/admin/system/health, Admin UI observability panel)
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from src.api.main import app, create_app
from src.db.migrations_v2 import apply_all_migrations
from src.security.crypto import generate_session_token
from src.security.observability import ObservabilityRegistry, classify_route_group, observability
from src.security.rate_limiter import SlidingWindowRateLimiter, get_client_ip

MASTER_DB = Path("master_database.sqlite")
ROOT_DIR = Path(__file__).resolve().parent.parent


def _make_isolated_db(tmp_path: Path, name: str = "phase7_test.sqlite") -> Path:
    db_file = tmp_path / name
    shutil.copy2(MASTER_DB, db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    apply_all_migrations(conn)
    conn.close()
    return db_file


# ==============================================================================
# 1. VERCEL COLD-START ROUTER SPLIT & LAZY ADMIN DISPATCH
# ==============================================================================


def test_public_split_avoids_eager_admin_imports_in_fresh_process():
    script = """
import os, sys, json
os.environ['VERCEL'] = '1'
os.environ['TURSO_DATABASE_URL'] = ''
from src.api.main import app
eager_check = {
    'public_only': app.state.public_only,
    'admin_routers_loaded': app.state.admin_routers_loaded,
    'routes_admin_payments_imported': 'src.admin.routes_admin_payments' in sys.modules,
    'routes_admin_questions_imported': 'src.admin.routes_admin_questions' in sys.modules,
    'admin_auth_service_imported': 'src.admin.auth_service' in sys.modules,
    'database_migrations_imported': 'src.database_migrations' in sys.modules,
    'sync_service_imported': 'src.sync.service' in sys.modules,
}
print(json.dumps(eager_check))
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    assert data["public_only"] is True
    assert data["admin_routers_loaded"] is False
    assert data["routes_admin_payments_imported"] is False
    assert data["routes_admin_questions_imported"] is False
    assert data["admin_auth_service_imported"] is False
    assert data["database_migrations_imported"] is False
    assert data["sync_service_imported"] is False


def test_public_split_disable_admin_and_lazy_mount_modes(monkeypatch):
    # Mode A: VERCEL_DISABLE_ADMIN=1 returns crisp 503 without mounting admin routes
    monkeypatch.setenv("VERCEL_DISABLE_ADMIN", "1")
    split_disabled = create_app(public_only=True)
    c_dis = TestClient(split_disabled)

    h_res = c_dis.get("/api/health")
    assert h_res.status_code == 200
    assert h_res.json()["router_mode"] == "public-split"
    assert h_res.json()["admin_routers_loaded"] is False
    assert h_res.json()["observability_ready"] is True

    adm_503 = c_dis.get("/api/admin/system/metrics")
    assert adm_503.status_code == 503
    assert split_disabled.state.admin_routers_loaded is False

    # Mode B: VERCEL_DISABLE_ADMIN=0 lazily attaches admin routes on first /api/admin/* hit
    monkeypatch.setenv("VERCEL_DISABLE_ADMIN", "0")
    split_lazy = create_app(public_only=True)
    assert split_lazy.state.admin_routers_loaded is False
    c_lazy = TestClient(split_lazy)

    adm_401 = c_lazy.get("/api/admin/system/metrics")
    assert adm_401.status_code == 401
    assert split_lazy.state.admin_routers_loaded is True


def test_vercel_entrypoint_health_check_hides_raw_tracebacks():
    from api.index import app as vercel_app

    vc = TestClient(vercel_app)
    res = vc.get("/api/health-check")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "rully-vercel"
    assert "mount_ms" in body
    assert body["import_ok"] is True
    assert "import_error" not in body


# ==============================================================================
# 2. SECURITY HARDENING: CSP, CORS, HSTS, PROXY IP & SANITIZED 500 HANDLER
# ==============================================================================


def test_security_headers_csp_hsts_and_cors():
    client = TestClient(app)

    # 1. User Mini App HTML: Telegram frame-ancestors allowed, NO unsafe-inline scripts
    res_home = client.get("/", headers={"x-forwarded-proto": "https"})
    assert res_home.status_code == 200
    assert res_home.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_home.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in res_home.headers
    assert "Strict-Transport-Security" in res_home.headers
    assert res_home.headers.get("X-Request-ID")
    assert res_home.headers.get("X-Process-Time-Ms")
    csp_user = res_home.headers.get("Content-Security-Policy", "")
    assert "https://web.telegram.org" in csp_user
    assert "'unsafe-inline'" not in csp_user.split("style-src")[0]
    assert "X-Frame-Options" not in res_home.headers

    # 2. Admin Panel: strict X-Frame-Options DENY + frame-ancestors 'none'
    res_adm = client.get("/admin/")
    assert res_adm.status_code == 200
    assert res_adm.headers.get("X-Frame-Options") == "DENY"
    csp_adm = res_adm.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp_adm

    # 3. CORS allows trusted Vercel/Telegram origins & blocks untrusted origin
    ok_cors = client.options(
        "/api/health",
        headers={"Origin": "https://rully-three.vercel.app", "Access-Control-Request-Method": "GET"},
    )
    assert ok_cors.headers.get("access-control-allow-origin") == "https://rully-three.vercel.app"

    bad_cors = client.options(
        "/api/health",
        headers={"Origin": "https://attacker.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad_cors.headers


def test_unhandled_exception_sanitized_no_stack_trace_leak():
    test_app = create_app(public_only=True)
    boom_router = APIRouter()

    @boom_router.get("/api/_test_boom_phase7")
    def _boom():
        raise RuntimeError("SECRET_INTERNAL_SQL_PATH_C:\\Users\\secret.db")

    test_app.include_router(boom_router)
    tc = TestClient(test_app, raise_server_exceptions=False)
    res = tc.get("/api/_test_boom_phase7")
    assert res.status_code == 500
    body = res.json()
    assert body["ok"] is False
    assert body["error"] == "Internal server error"
    assert len(body["request_id"]) >= 8
    assert "SECRET_INTERNAL_SQL_PATH" not in res.text


def test_proxy_client_ip_extraction_and_rate_limiter_stats(monkeypatch):
    class _Req:
        def __init__(self, headers, host="10.0.0.1"):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    assert get_client_ip(_Req({"cf-connecting-ip": "198.51.100.12"})) == "198.51.100.12"
    assert get_client_ip(_Req({"x-forwarded-for": "203.0.113.9, 10.0.0.2"})) == "203.0.113.9"
    assert get_client_ip(_Req({"x-real-ip": "192.0.2.55"})) == "192.0.2.55"
    assert get_client_ip(_Req({})) == "10.0.0.1"

    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("ENABLE_TEST_RATE_LIMIT", "true")
    rl = SlidingWindowRateLimiter(maxsize=10)
    assert rl.is_allowed("ip:1", max_requests=2, window_seconds=60)[0] is True
    assert rl.is_allowed("ip:1", max_requests=2, window_seconds=60)[0] is True
    allowed, rem, retry = rl.is_allowed("ip:1", max_requests=2, window_seconds=60)
    assert allowed is False
    assert rem == 0
    assert retry > 0
    assert rl.stats()["rejections_total"] == 1


# ==============================================================================
# 3. OBSERVABILITY METRICS, ADMIN TELEMETRY ENDPOINTS & ADMIN UI CHECKS
# ==============================================================================


def test_observability_registry_percentiles_and_rings():
    reg = ObservabilityRegistry(latency_window=50, recent_cap=5)
    reg.set_boot_metadata("public-split", 14.5)

    assert classify_route_group("/api/auth/telegram") == "auth_user"
    assert classify_route_group("/api/srs/queue") == "theory_quiz"
    assert classify_route_group("/api/ai/chat") == "ai_ustoz"
    assert classify_route_group("/api/admin/system/health") == "admin"

    for ms in (12.0, 18.0, 25.0, 40.0, 620.0):
        reg.record_request("GET", "/api/categories", 200, ms, "req-a")
    reg.record_request("POST", "/api/ai/chat", 500, 1100.0, "req-err")

    snap = reg.snapshot()
    assert snap["router_mode"] == "public-split"
    assert snap["cold_start_ms"] == 14.5
    assert snap["total_requests"] == 6
    assert snap["errors_5xx"] == 1
    assert snap["routes"]["theory_quiz"]["count"] == 5
    assert snap["routes"]["theory_quiz"]["p50_ms"] == 25.0
    assert snap["routes"]["theory_quiz"]["p95_ms"] == 620.0
    assert len(snap["slow_requests"]) == 2
    assert len(snap["recent_errors"]) == 1


def test_admin_observability_metrics_and_health_endpoints(tmp_path, monkeypatch):
    import src.admin.auth_service as admin_auth
    import src.admin.routes_admin_logs as ral

    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _make_isolated_db(tmp_path)
    token = generate_session_token()
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
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
    monkeypatch.setattr(ral, "DB_PATH", str(db_file))
    monkeypatch.setattr(ral, "_get_connection", lambda: sqlite3.connect(str(db_file)))

    # Fix row_factory cleanly on isolated connection helper
    def _iso_conn():
        c = sqlite3.connect(str(db_file))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(ral, "_get_connection", _iso_conn)

    observability.reset()
    client = TestClient(app)

    # Unauthenticated blocked cleanly
    assert client.get("/api/admin/system/metrics").status_code == 401

    # Hit public health endpoint so metrics record traffic
    assert client.get("/api/health").status_code == 200

    res_metrics = client.get("/api/admin/system/metrics", headers={"Authorization": f"Bearer {token}"})
    assert res_metrics.status_code == 200
    mdata = res_metrics.json()
    assert mdata["ok"] is True
    assert mdata["metrics"]["total_requests"] >= 1
    assert "health" in mdata["metrics"]["routes"]
    assert "tracked_keys" in mdata["rate_limiter"]

    res_health = client.get("/api/admin/system/health", headers={"Authorization": f"Bearer {token}"})
    assert res_health.status_code == 200
    hdata = res_health.json()
    assert hdata["ok"] is True
    assert hdata["overall_status"] == "HEALTHY"
    assert hdata["database"]["integrity_check"] == "ok"
    assert "observability" in hdata
    assert "catalog_version" in hdata


def test_admin_ui_observability_panel_and_js_syntax():
    admin_html = (ROOT_DIR / "static" / "admin" / "index.html").read_text(encoding="utf-8")
    assert "acc-observability" in admin_html
    assert "obs-latency-val" in admin_html
    assert "obs-audit-logs-list" in admin_html
    assert "/static/admin/admin.js?v=2.9.0" in admin_html
    assert "/static/admin/admin.css?v=2.8.0" in admin_html

    chk = subprocess.run(["node", "--check", "static/admin/admin.js"], capture_output=True, text=True)
    assert chk.returncode == 0, chk.stderr
