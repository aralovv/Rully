"""
Phase 4 Verification Suite: Architecture, Zero-Waterfall Turso RT Budgets,
Honest User Metrics ("Ko'rsatkichlar"), Hard Purge (4C), and Simplified Nazariya IA (4D).
"""

import json
import os
import shutil
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.deps import get_db
from src.api.security import generate_dev_init_data
from src.avtotest_product import AvtotestProductEngine
from src.bot.bot import create_bot_app
from src.bot.database import BotDatabase
from src.database_migrations import run_migrations
from src.db.migrations_v2 import verify_phase4_schema_parity
from src.security.crypto import generate_session_token

ROOT_DIR = Path(__file__).resolve().parent.parent
MASTER_DB = ROOT_DIR / "master_database.sqlite"


def _init_temp_db(tmp_path: Path, name: str = "phase4_test.sqlite") -> Path:
    db_file = tmp_path / name
    shutil.copy2(MASTER_DB, db_file)
    run_migrations(str(db_file))
    return db_file


class RoundTripSpy:
    """Counts genuine SQLite/Turso round-trips (each batch or unbatched execute = 1 RT)."""

    def __init__(self):
        self.count = 0
        self.ops = []

    def reset(self):
        self.count = 0
        self.ops.clear()

    def record(self, kind: str, detail: str = ""):
        self.count += 1
        self.ops.append((kind, detail))


@contextmanager
def track_round_trips(db_obj: BotDatabase, admin_db_path: str = None):
    import src.db_adapter as db_adapter

    spy = RoundTripSpy()

    orig_fetch_batch = db_adapter.fetch_batch_dicts
    orig_exec_batch = db_adapter.execute_batch
    in_batch = [False]

    def tracked_fetch(conn, stmts):
        spy.record("batch_read", f"{len(stmts)} stmts")
        in_batch[0] = True
        try:
            return orig_fetch_batch(conn, stmts)
        finally:
            in_batch[0] = False

    def tracked_exec(conn, stmts):
        spy.record("batch_write", f"{len(stmts)} stmts")
        in_batch[0] = True
        try:
            return orig_exec_batch(conn, stmts)
        finally:
            in_batch[0] = False

    class TrackedCursor:
        def __init__(self, inner):
            self._inner = inner

        def execute(self, sql, params=()):
            if not in_batch[0]:
                spy.record("execute", sql.strip().split("\n")[0][:60])
            return self._inner.execute(sql, params)

        def executemany(self, sql, seq):
            if not in_batch[0]:
                spy.record("executemany", sql.strip().split("\n")[0][:60])
            return self._inner.executemany(sql, seq)

        def fetchone(self):
            return self._inner.fetchone()

        def fetchall(self):
            return self._inner.fetchall()

        @property
        def rowcount(self):
            return self._inner.rowcount

        @property
        def lastrowid(self):
            return self._inner.lastrowid

        def __getattr__(self, name):
            return getattr(self._inner, name)

    class TrackedConn:
        def __init__(self, inner):
            self._inner = inner

        def cursor(self):
            return TrackedCursor(self._inner.cursor())

        def execute(self, sql, params=()):
            if not in_batch[0]:
                spy.record("conn_execute", sql.strip().split("\n")[0][:60])
            return self._inner.execute(sql, params)

        def commit(self):
            return self._inner.commit()

        def rollback(self):
            return self._inner.rollback()

        def close(self):
            return self._inner.close()

        def __enter__(self):
            self._inner.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._inner.__exit__(exc_type, exc, tb)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    orig_get_conn = db_obj._get_connection
    orig_global_conn = db_adapter.get_db_connection

    @contextmanager
    def wrapped_db_conn():
        with orig_get_conn() as c:
            yield TrackedConn(c)

    def wrapped_global_conn(db_path=None):
        target = admin_db_path or db_obj.db_path
        return TrackedConn(orig_global_conn(db_path or target))

    patches = [
        patch("src.db_adapter.fetch_batch_dicts", side_effect=tracked_fetch),
        patch("src.db_adapter.execute_batch", side_effect=tracked_exec),
        patch("src.db.repos.base.fetch_batch_dicts", side_effect=tracked_fetch),
        patch("src.db.repos.base.execute_batch", side_effect=tracked_exec),
        patch("src.db_adapter.get_db_connection", side_effect=wrapped_global_conn),
        patch.object(db_obj, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.users, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.sessions, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.exams, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.srs, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.payments, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.analytics, "_get_connection", side_effect=wrapped_db_conn),
        patch.object(db_obj.editorial, "_get_connection", side_effect=wrapped_db_conn),
    ]
    for p in patches:
        p.start()
    try:
        yield spy
    finally:
        for p in reversed(patches):
            p.stop()


def test_phase4_modular_repos_shared_engine_and_db_backed_sm2(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _init_temp_db(tmp_path)
    db_w1 = BotDatabase(str(db_file))
    db_w2 = BotDatabase(str(db_file))

    # 1. Domain repository composition + thin facade check
    for attr in ("users", "sessions", "exams", "srs", "payments", "analytics", "editorial"):
        assert hasattr(db_w1, attr), f"Missing modular repo {attr}"

    db_facade_src = (ROOT_DIR / "src" / "bot" / "database.py").read_text(encoding="utf-8")
    assert "_PRE_ANSWER_SRS_CACHE" not in db_facade_src
    assert len(db_facade_src.splitlines()) <= 600

    # 2. Cross-worker DB-backed SM-2 prev_state_json recalibration
    uid = 994001
    db_w1.get_or_create_user(uid, "sm2_worker_test")
    cid = "CANON-YHQ-0001"
    r1 = db_w1.record_srs_review(uid, cid, quality=1)
    assert r1["repetitions"] == 0
    assert r1["lapses"] == 1

    # Fresh worker instance reads prev_state_json directly from DB without process cache
    r_recal = db_w2.record_srs_review(uid, cid, quality=4, recalibrate=True)
    assert r_recal["repetitions"] == 1
    assert r_recal["lapses"] == 0

    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute(
            "SELECT prev_state_json, last_quality FROM user_question_srs WHERE user_id = ? AND canonical_id = ?",
            (uid, cid),
        ).fetchone()
        assert row is not None and row[0] is not None and int(row[1]) == 4

    # 3. Single shared AvtotestProductEngine injection for Bot app
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    shared_eng = AvtotestProductEngine(str(db_file))
    bot_res = create_bot_app(product_engine=shared_eng)
    assert isinstance(bot_res, tuple) and len(bot_res) >= 4
    assert bot_res[3] is shared_eng

    # 4. Question sync workflow + async loop safety check
    yml = ROOT_DIR / ".github" / "workflows" / "question_sync.yml"
    ci_script = ROOT_DIR / "scripts" / "ci_sync_questions.py"
    assert yml.exists() and ci_script.exists()
    sync_src = (ROOT_DIR / "src" / "sync" / "service.py").read_text(encoding="utf-8")
    assert "get_running_loop" in sync_src


def test_phase4_zero_waterfall_turso_rt_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("ADMIN_BOT_TOKEN", "")
    db_file = _init_temp_db(tmp_path)
    db = BotDatabase(str(db_file))
    uid = 8809526955
    db.get_or_create_user(uid, "rt_budget_user")

    import src.api.routes_auth as rauth
    import src.api.routes_theory as rtheory
    import src.admin.auth_service as admin_auth
    import src.admin.routes_admin_payments as rap
    import src.admin.routes_admin_questions as raq
    import src.admin.routes_admin_dashboard as rad

    # Seed 5 unmatched payments to ensure zero N+1 query scaling on admin unmatched queue
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        admin_id = conn.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'").fetchone()[0]
        token = generate_session_token()
        conn.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', datetime('now'), datetime('now', '+2 hours'), 0, datetime('now'))
            """,
            (token, admin_id),
        )
        for idx in range(5):
            cur = conn.execute(
                """
                INSERT INTO payment_events (
                    event_fingerprint, source_chat, message_id, transaction_type,
                    incoming_amount_uzs, resulting_balance_uzs, card_suffix, payment_source,
                    transaction_timestamp, raw_message, status, created_at
                ) VALUES (?, 'Humocardbot', ?, 'INCOMING', ?, 100000, '5370', 'HUMO', datetime('now'), 'raw', 'UNMATCHED', datetime('now'))
                """,
                (f"fp-p4-{idx}", 99400 + idx, 49000 + idx * 1000),
            )
            ev_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO unmatched_payments (
                    event_id, amount_uzs, card_suffix, payment_source,
                    transaction_timestamp, status, created_at
                ) VALUES (?, ?, '5370', 'HUMO', datetime('now'), 'UNRESOLVED', datetime('now'))
                """,
                (ev_id, 49000 + idx * 1000),
            )
        conn.commit()

    orig_engine = rtheory.engine
    rtheory.engine = AvtotestProductEngine(str(db_file))
    rauth.invalidate_auth_cache(uid)
    monkeypatch.setattr(admin_auth, "DB_PATH", str(db_file))
    monkeypatch.setattr(rap, "DB_PATH", str(db_file))
    monkeypatch.setattr(raq.sync_service, "db_path", str(db_file))
    monkeypatch.setattr(rad, "DB_PATH", str(db_file), raising=False)
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)
    try:
        with track_round_trips(db, admin_db_path=str(db_file)) as spy:
            # 1. Unified Mini App boot
            spy.reset()
            boot_res = client.post("/api/miniapp/boot", json={"init_data": None, "lang": "uz_latn"})
            assert boot_res.status_code == 200
            assert spy.count <= 2, f"/api/miniapp/boot exceeded RT budget: {spy.count} -> {spy.ops}"

            # 2. Session start
            spy.reset()
            start_res = client.post("/api/session/start", json={"session_type": "EXAM", "language": "uz_latn"})
            assert start_res.status_code == 200
            sid = start_res.json()["session_id"]
            qid = start_res.json()["questions"][0]["canonical_id"]
            assert spy.count <= 2, f"/api/session/start exceeded RT budget: {spy.count} -> {spy.ops}"

            # 3. Session answer
            spy.reset()
            ans_res = client.post("/api/session/answer", json={"session_id": sid, "canonical_id": qid, "selected_key": "A", "response_time_ms": 1400})
            assert ans_res.status_code == 200
            assert spy.count <= 2, f"/api/session/answer exceeded RT budget: {spy.count} -> {spy.ops}"

            # 4. Session finish
            spy.reset()
            fin_res = client.post("/api/session/finish", json={"session_id": sid, "time_elapsed_seconds": 12})
            assert fin_res.status_code == 200
            assert spy.count <= 2, f"/api/session/finish exceeded RT budget: {spy.count} -> {spy.ops}"

            # 5. Session review
            spy.reset()
            rev_res = client.get(f"/api/session/{sid}/review?lang=uz_latn")
            assert rev_res.status_code == 200
            assert spy.count <= 2, f"/api/session/{{sid}}/review exceeded RT budget: {spy.count} -> {spy.ops}"

        hdrs = {"Authorization": f"Bearer {token}"}

        # Count raw admin endpoints cleanly using direct patched SQLite conn proxy
        orig_get_db_conn = __import__("src.db_adapter", fromlist=["get_db_connection"]).get_db_connection
        rt_counter = [0]

        def admin_conn_spy(db_path=None):
            conn = orig_get_db_conn(str(db_file))
            class _AdminConnWrap:
                def __init__(self, c): self._c = c
                def cursor(self):
                    cur = self._c.cursor()
                    class _AdminCur:
                        def execute(self, s, p=()):
                            rt_counter[0] += 1
                            return cur.execute(s, p)
                        def __getattr__(self, n): return getattr(cur, n)
                    return _AdminCur()
                def execute(self, s, p=()):
                    rt_counter[0] += 1
                    return self._c.execute(s, p)
                def __enter__(self): self._c.__enter__(); return self
                def __exit__(self, *a): return self._c.__exit__(*a)
                def __getattr__(self, n): return getattr(self._c, n)
            return _AdminConnWrap(conn)

        import src.db_adapter as da
        orig_fb = da.fetch_batch_dicts
        def fb_counted(conn, stmts):
            before = rt_counter[0]
            res = orig_fb(conn, stmts)
            rt_counter[0] = before + 1
            return res

        with patch("src.admin.auth_service.get_db_connection", side_effect=admin_conn_spy), \
             patch("src.admin.routes_admin_dashboard.get_db_connection", side_effect=admin_conn_spy), \
             patch("src.admin.routes_admin_payments.get_db_connection", side_effect=admin_conn_spy), \
             patch("src.admin.routes_admin_questions.get_db_connection", side_effect=admin_conn_spy), \
             patch("src.db.provenance_classifier.fetch_batch_dicts", side_effect=fb_counted), \
             patch("src.admin.routes_admin_payments.fetch_batch_dicts", side_effect=fb_counted), \
             patch("src.admin.routes_admin_dashboard.fetch_batch_dicts", side_effect=fb_counted):

            rt_counter[0] = 0
            ov = client.get("/api/admin/overview/boot", headers=hdrs)
            assert ov.status_code == 200 and ov.json().get("ok") is True
            assert rt_counter[0] <= 3, f"Admin overview boot RTs: {rt_counter[0]}"

            rt_counter[0] = 0
            unm = client.get("/api/admin/payments/unmatched", headers=hdrs)
            assert unm.status_code == 200 and len(unm.json()["unmatched"]) >= 5
            assert rt_counter[0] <= 3, f"Admin unmatched RTs (N=5): {rt_counter[0]}"

            rt_counter[0] = 0
            ed = client.get("/api/admin/questions/editorial?limit=5", headers=hdrs)
            assert ed.status_code == 200 and ed.json()["success"] is True
            assert rt_counter[0] <= 3, f"Admin editorial RTs: {rt_counter[0]}"

            # Stale (>120s) admin session triggering activity touch STILL stays <= 3 RTs on editorial & overview
            with sqlite3.connect(str(db_file)) as conn:
                conn.execute(
                    "UPDATE admin_sessions SET last_activity_at = datetime('now', '-10 minutes') WHERE session_id = ?",
                    (token,),
                )
                conn.commit()
            rt_counter[0] = 0
            ed_stale = client.get("/api/admin/questions/editorial?limit=5", headers=hdrs)
            assert ed_stale.status_code == 200 and ed_stale.json()["success"] is True
            assert rt_counter[0] <= 3, f"Admin editorial stale-session RTs: {rt_counter[0]}"
    finally:
        rtheory.engine = orig_engine
        app.dependency_overrides.clear()


def test_phase4_honest_metrics_utc5_and_mistake_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _init_temp_db(tmp_path)
    db = BotDatabase(str(db_file))
    engine = AvtotestProductEngine(str(db_file))
    uid = 994002
    db.get_or_create_user(uid, "honest_metrics_user")

    # 1. Brand-new user has zero phantom percentages
    cats = engine.get_categories("uz_latn")
    assert len(cats) == 41
    bundle = db.get_user_full_auth_bundle(uid, categories=cats, engine_total_questions=1327)
    st = bundle["stats"]
    assert st["accuracy"] == 0.0
    assert st["readiness_score"] == 0.0
    assert st["pass_rate"] == 0.0
    assert st["srs_summary"]["retention_rate"] == 0.0
    assert st["topic_count_total"] == 41
    assert st["total_bank_questions"] == 1327
    assert st["streak"] == bundle["streak"]["current_streak"] == 0

    # 2. Mistake drill resolution does NOT inflate accuracy
    q_obj = engine.get_question("CANON-YHQ-0001", language="uz_latn", include_answer_key=True)
    wrong_key = next(o.option_key for o in q_obj.options if o.option_key != q_obj.correct_option_key)
    exam_s = db.create_session(uid, "EXAM", "uz_latn", ["CANON-YHQ-0001"])
    db.process_session_answer(exam_s["session_id"], uid, "CANON-YHQ-0001", wrong_key, q_obj.correct_option_key, False, "EXAM")
    stats_after_wrong = db.get_user_stats(uid)
    assert stats_after_wrong["unresolved_mistakes"] == 1
    assert stats_after_wrong["accuracy"] == 0.0

    mistake_s = db.create_session(uid, "MISTAKES", "uz_latn", ["CANON-YHQ-0001"])
    db.process_session_answer(mistake_s["session_id"], uid, "CANON-YHQ-0001", q_obj.correct_option_key, q_obj.correct_option_key, True, "MISTAKES")
    stats_after_fix = db.get_user_stats(uid)
    assert stats_after_fix["unresolved_mistakes"] == 0
    assert stats_after_fix["accuracy"] == 0.0

    # 3. Asia/Tashkent UTC+5 midnight rollover increments streak 1 -> 2 across 19:00 UTC boundary
    day1_tashkent = datetime(2026, 5, 10, 23, 55, 0, tzinfo=timezone(timedelta(hours=5)))
    day2_tashkent = datetime(2026, 5, 11, 0, 5, 0, tzinfo=timezone(timedelta(hours=5)))
    uid_tz = 994003
    db.get_or_create_user(uid_tz, "tz_user")
    s1 = db.create_session(uid_tz, "CATEGORY", "uz_latn", ["CANON-YHQ-0001"], category_id=1)
    s2 = db.create_session(uid_tz, "CATEGORY", "uz_latn", ["CANON-YHQ-0002"], category_id=1)

    with patch("src.db.repos.sessions_repo.tashkent_now", return_value=day1_tashkent), \
         patch("src.db.repos.analytics_repo.tashkent_now", return_value=day1_tashkent):
        res1 = db.process_session_answer(s1["session_id"], uid_tz, "CANON-YHQ-0001", "A", "A", True, "CATEGORY")
        assert res1["streak"]["current_streak"] == 1

    with patch("src.db.repos.sessions_repo.tashkent_now", return_value=day2_tashkent), \
         patch("src.db.repos.analytics_repo.tashkent_now", return_value=day2_tashkent):
        read_mid = db.get_learning_streak(uid_tz)
        assert read_mid["current_streak"] == 1
        assert read_mid["today_questions_count"] == 0
        res2 = db.process_session_answer(s2["session_id"], uid_tz, "CANON-YHQ-0002", "A", "A", True, "CATEGORY")
        assert res2["streak"]["current_streak"] == 2
        assert res2["streak"]["today_questions_count"] == 1


def test_phase4_hard_purge_migration_005_and_nazariya_i18n(tmp_path, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _init_temp_db(tmp_path)

    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        parity = verify_phase4_schema_parity(conn)
        assert parity["passed"] is True, parity
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "practical_checklist" not in tables
        assert "practical_quiz_results" not in tables
        assert "telegram_users" in tables and "user_question_srs" in tables
        assert conn.execute("PRAGMA integrity_check").fetchone()[0].lower() == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    # Removed endpoints return 404; modules stay 200
    db = BotDatabase(str(db_file))
    db.get_or_create_user(8809526955, "purge_user")
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    try:
        for gone in ("/api/amaliy/checklist", "/api/amaliy/scenarios"):
            assert client.get(gone).status_code == 404
        assert client.get("/api/amaliy/modules?lang=uz_latn").json()["total"] == 10
    finally:
        app.dependency_overrides.clear()

    # Removed static image and zero 4C references
    assert not (ROOT_DIR / "static" / "img" / "cobalt_wheel.webp").exists()
    for rel in (
        "static/index.html",
        "static/css/rully.css",
        "static/js/views/amaliy.js",
        "static/js/views/prepare.js",
        "static/js/views/home.js",
        "static/js/views/profile.js",
        "static/js/app.js",
        "static/js/core/state.js",
        "static/js/translations.js",
    ):
        txt = (ROOT_DIR / rel).read_text(encoding="utf-8")
        for forbidden in ("SIM_MANEUVERS", "avtodrom-stage", "renderChecklistTab", "renderScenariosTab", "tab_checklist", "tab_scenarios", "milestone_avtodrom_pro"):
            assert forbidden not in txt, f"Leftover 4C symbol {forbidden} in {rel}"

    # Workstream 4D: exact 4-subtab prepare.js + clean hash sync + i18n parity
    prep_txt = (ROOT_DIR / "static" / "js" / "views" / "prepare.js").read_text(encoding="utf-8")
    for tok in ('data-prep-tab="tickets"', 'data-prep-tab="topics"', 'data-prep-tab="drill"', 'data-prep-tab="reference"', 'data-ref-mode="signs"', 'data-ref-mode="rules"'):
        assert tok in prep_txt

    i18n_check = r"""
    const fs = require('fs'), vm = require('vm');
    const ctx = { window: {} };
    vm.runInNewContext(fs.readFileSync('static/js/translations.js', 'utf8'), ctx);
    const I = ctx.window.I18N;
    const keys = Object.keys(I.uz_latn).sort();
    for (const l of ['uz_cyrl', 'ru']) {
      if (JSON.stringify(Object.keys(I[l]).sort()) !== JSON.stringify(keys)) process.exit(2);
    }
    if (I.ru.stat_tests_taken !== 'Попыток экзамена') process.exit(3);
    if (!I.uz_latn.pillar_cov_desc.includes('41')) process.exit(4);
    for (const l of ['uz_latn', 'uz_cyrl', 'ru']) {
      const b = JSON.parse(fs.readFileSync(`static/i18n/${l}.json`, 'utf8'));
      if (JSON.stringify(b) !== JSON.stringify(I[l])) process.exit(5);
    }
    const transRaw = fs.readFileSync('static/js/translations.js', 'utf8');
    // Check ZERO duplicate property keys inside each language block
    for (const lang of ['uz_latn', 'uz_cyrl', 'ru']) {
      const m = transRaw.match(new RegExp(lang + ':\\s*\\{([\\s\\S]*?)\\n  \\}'));
      if (!m) process.exit(6);
      const seen = new Set();
      for (const km of m[1].matchAll(/^\s*([a-zA-Z0-9_]+):/gm)) {
        if (seen.has(km[1])) { console.error('DUP:', lang, km[1]); process.exit(7); }
        seen.add(km[1]);
      }
    }
    console.log('I18N_OK', keys.length);
    """
    node_run = subprocess.run(["node", "-e", i18n_check], cwd=str(ROOT_DIR), capture_output=True, text=True)
    assert node_run.returncode == 0, node_run.stdout + node_run.stderr


def test_phase4_frontend_backend_schema_contracts_e2e(tmp_path, monkeypatch):
    """Executes real prepare.js, home.js, profile.js, and app.js against live FastAPI payloads."""
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    db_file = _init_temp_db(tmp_path)
    db = BotDatabase(str(db_file))
    engine = AvtotestProductEngine(str(db_file))
    uid = 8809526955
    db.get_or_create_user(uid, "schema_e2e_user")

    import src.api.routes_auth as rauth
    import src.api.routes_theory as rtheory

    orig_engine = rtheory.engine
    rtheory.engine = engine
    rauth.invalidate_auth_cache(uid)

    # Seed real bookmark, mistake, weak topic answer, and due SRS card
    q_obj = engine.get_question("CANON-YHQ-0001", language="uz_latn", include_answer_key=True)
    wrong_key = next(o.option_key for o in q_obj.options if o.option_key != q_obj.correct_option_key)
    db.toggle_bookmark(uid, "CANON-YHQ-0001")
    sess = db.create_session(uid, "CATEGORY", "uz_latn", ["CANON-YHQ-0001"], category_id=q_obj.category_id)
    db.process_session_answer(sess["session_id"], uid, "CANON-YHQ-0001", wrong_key, q_obj.correct_option_key, False, "CATEGORY")
    db.record_srs_review(uid, "CANON-YHQ-0001", quality=1, now_dt=datetime.utcnow() - timedelta(days=2))

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    try:
        boot_json = client.post("/api/miniapp/boot", json={"init_data": None, "lang": "uz_latn"}).json()
        tickets_json = client.get("/api/tickets?lang=uz_latn").json()
        srs_json = client.get("/api/srs/queue?lang=uz_latn&limit=10").json()
        bookmarks_json = client.get("/api/bookmarks?lang=uz_latn").json()
    finally:
        rtheory.engine = orig_engine
        app.dependency_overrides.clear()

    payload_file = tmp_path / "e2e_payloads.json"
    payload_file.write_text(
        json.dumps({"boot": boot_json, "tickets": tickets_json, "srs": srs_json, "bookmarks": bookmarks_json}),
        encoding="utf-8",
    )

    node_runner = rf"""
    const fs = require('fs');
    const vm = require('vm');
    const data = JSON.parse(fs.readFileSync({json.dumps(str(payload_file))}, 'utf8'));

    const elements = {{}};
    function makeEl(id) {{
      return {{
        id,
        innerHTML: '',
        value: '',
        checked: true,
        classList: {{ toggle: () => {{}}, add: () => {{}}, remove: () => {{}} }},
        dataset: {{}},
        addEventListener: () => {{}},
        querySelectorAll: () => [],
      }};
    }}
    ['view-home','view-tests','prepare-subtab-body','view-amaliy','view-ai','view-profile','view-quiz','view-results'].forEach(id => elements[id] = makeEl(id));

    const sandbox = {{
      window: {{
        location: {{ protocol: 'https:', hash: '#tests/reference/rules', search: '' }},
        history: {{ replaceState: (_a,_b,u) => {{ sandbox.lastHash = u; }} }},
        addEventListener: () => {{}},
      }},
      document: {{
        readyState: 'complete',
        getElementById: (id) => {{
          if (id === 'btn-launch-adaptive') return {{ addEventListener: (ev, fn) => {{ if (ev === 'click') sandbox.adaptiveClick = fn; }} }};
          return elements[id] || null;
        }},
        querySelectorAll: () => [],
        addEventListener: () => {{}},
        body: {{ classList: {{ remove: () => {{}}, add: () => {{}} }} }},
      }},
      console,
      Date,
      Math,
      JSON,
      Number,
      String,
      Array,
      Object,
      Boolean,
      Set,
      Map,
      URLSearchParams,
      encodeURIComponent,
      decodeURIComponent,
      lastHash: '',
      adaptiveClick: null,
      paywallOpened: false,
      startedSessions: [],
    }};
    sandbox.window.window = sandbox.window;
    sandbox.window.document = sandbox.document;
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    for (const rel of ['static/js/icons.js','static/js/translations.js','static/js/core/state.js','static/js/views/home.js','static/js/views/prepare.js','static/js/views/profile.js']) {{
      vm.runInContext(fs.readFileSync(rel, 'utf8'), sandbox);
    }}

    const R = sandbox.window.RULLY;
    R.theme = {{ pref: 'auto', apply: () => {{}} }};
    R.navigateTo = () => {{}};
    R.startSession = (cfg) => sandbox.startedSessions.push(cfg);
    R.openPaywallModal = () => {{ sandbox.paywallOpened = true; }};
    R.openModal = () => {{}};
    R.renderSignsExplorer = () => {{}};
    R.renderLawExplorer = () => {{}};
    R.openInfoModal = () => {{}};
    R.openCheatsheetModal = () => {{}};
    R.openLights = () => {{}};

    const boot = data.boot;
    R.state.isGuest = false;
    R.state.authPending = false;
    R.state.lang = 'uz_latn';
    R.state.user = boot.user;
    R.state.subscription = boot.subscription;
    R.state.freeTier = boot.free_tier;
    R.state.stats = boot.stats;
    R.state.streak = boot.streak;
    R.state.categories = boot.categories;
    R.state.analytics = boot.analytics;
    R.state.history = boot.history;
    R.state.bookmarksCount = boot.bookmarks_count;
    R.state.tickets = data.tickets.tickets;
    R.state.srsQueue = data.srs;
    R.state.bookmarksList = data.bookmarks.questions;
    R.state.bookmarksLoaded = true;

    // 1. Render Home
    R.renderHome();
    if (elements['view-home'].innerHTML.includes('undefined')) throw new Error('Home HTML contains undefined');

    // 2. Render Tickets, Topics, Drill
    for (const tab of ['tickets', 'topics', 'drill', 'reference']) {{
      R.state.prepareSubtab = tab;
      R.renderPrepare();
      const html = elements['prepare-subtab-body'].innerHTML;
      if (html.includes('undefined')) throw new Error(`Prepare ${{tab}} contains undefined`);
      if (tab === 'tickets' && !html.includes('20 ta savol')) throw new Error('Tickets missing question_count');
      if (tab === 'topics' && !html.includes('1 !')) throw new Error('Topics missing unresolved_mistakes badge');
      if (tab === 'drill') {{
        if (!html.includes('CANON-YHQ-0001') && !html.includes(data.bookmarks.questions[0].question_text.slice(0, 12))) {{
          throw new Error('Drill missing bookmarks or SRS items rendering');
        }}
        if (sandbox.adaptiveClick) sandbox.adaptiveClick();
        if (sandbox.paywallOpened) throw new Error('Free user wrongly paywalled on ADAPTIVE');
        if (!sandbox.startedSessions.some(s => s.session_type === 'ADAPTIVE')) throw new Error('ADAPTIVE did not launch');
      }}
    }}

    // 3. Render Profile -> weak category button rendered from analytics.weak_categories.attempts
    R.renderProfile();
    const profHtml = elements['view-profile'].innerHTML;
    if (profHtml.includes('undefined')) throw new Error('Profile HTML contains undefined');
    if (!profHtml.includes('data-prof-weak-cat')) throw new Error('Profile weak_categories empty despite attempt <80%');
    console.log('E2E_CONTRACT_OK');
    """
    res = subprocess.run(["node", "-e", node_runner], cwd=str(ROOT_DIR), capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "E2E_CONTRACT_OK" in res.stdout
