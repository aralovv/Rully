"""
Phase 3 Comprehensive Test Suite — Workstreams 3A, 3B, 3C, 3D + Offline AI Evaluation Harness.

Coverage:
  3A: VMQ 172 corpus (vmq_articles) + unified vmq172_law.py chapter/sign SSOT
  3B: Corpus quality — categories (no id=41, id=9 clean), Class-A fixes, CQ cleanup,
      canonical_id-keyed image_scenes.json, canonical_bundle.json integrity
  3C: AI Ustoz 3.0 — true :streamGenerateContent?alt=sse streaming, thought filtering,
      thoughtSignature preservation, 4-round toolConfig.NONE synthesis, mid-stream disconnect/503
      usage_date rollback, chunk-boundary ID sanitizer, cached get_provenance_select_sql,
      apostrophe search normalization, is_resolved=0 filter, lookup_vmq_law, observability
  3D: Batched bulk-approve + sibling auto-close, bulk-reject, 3-lang ai-draft upsert,
      source_type/trilingual q search, catalog/status & catalog/rebuild, multi-card CRUD &
      16-digit/404 validation, plan PUT price audit & ordering
  Offline AI Evaluation Harness: grounding fidelity, zero invented clauses, language purity
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json
import os
import re
import secrets
import shutil
import sqlite3
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from src.api.main import app
from src.api.security import generate_dev_init_data
from src.db_adapter import get_db_connection
from src.security.crypto import hash_password


def _create_admin_headers(db_path: str, username: str = "p3_admin", role: str = "SUPERADMIN") -> Dict[str, str]:
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    exp_str = (now_dt + timedelta(hours=4)).isoformat()
    token = f"adm_p3_{role.lower()}_{secrets.token_hex(8)}"
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
                (username, hash_password("Phase3AdminPw!2026"), 771122, role, now_str),
            )
            admin_id = c.lastrowid
        c.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest_p3', ?, ?, 0, ?)
            """,
            (token, admin_id, now_str, exp_str, now_str),
        )
        conn.commit()
    return {"X-Admin-Session": token}


def _copy_isolated_db(tmp_path, name: str = "p3_iso.sqlite") -> str:
    src = os.getenv("DB_PATH", "master_database.sqlite")
    dst = str(tmp_path / name)
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dst)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    return dst


# ─── 3A: VMQ 172 Statutory Law Corpus ───────────────────────────────────────

class TestWorkstream3A:
    def test_vmq172_law_chapters_and_17_1_and_annexes(self):
        from src.db.vmq172_law import CHAPTER_BY_CODE, VMQ172_CHAPTERS_DATA, get_chapter_title

        assert len(VMQ172_CHAPTERS_DATA) >= 34
        for num in range(1, 30):
            assert str(num) in CHAPTER_BY_CODE, f"Missing chapter {num}"
        assert "17-1" in CHAPTER_BY_CODE
        for idx in range(1, 5):
            assert f"annex-{idx}" in CHAPTER_BY_CODE
        assert get_chapter_title(17, "uz_latn")
        assert get_chapter_title("17-1", "ru")

    def test_vmq172_law_find_clause(self):
        from src.db.vmq172_law import find_clause

        c78 = find_clause(78)
        assert c78 is not None and "60" in (c78.get("text_uz") or "")
        c115_1 = find_clause("115-1")
        assert c115_1 is not None
        # Ensure Chapter 2 12^1..12^3 do not collide with Chapters 19..20 clauses 121..123
        c12_1 = find_clause("12-1")
        c121 = find_clause("121")
        assert c12_1 is not None and str(c12_1.get("chapter_code")) == "2"
        assert c121 is not None and str(c121.get("chapter_code")) == "19"

    def test_vmq172_law_road_signs_canonical_map(self):
        from src.db.vmq172_law import find_sign_or_marking, get_road_signs_canonical_map
        from src.verification_engine import ROAD_SIGNS_CANONICAL

        sign_map = get_road_signs_canonical_map()
        assert isinstance(sign_map, dict)
        assert len(sign_map) > 0
        # Ensure calendar date tokens are not indexed as road signs
        assert "15.05.2025" not in sign_map
        # Annex 1 road signs take precedence over Annex 2 markings on shared codes
        assert "sohil" in sign_map["1.10"][0].lower()
        assert "berk" in ROAD_SIGNS_CANONICAL["5.19.1"][0].lower()
        assert find_sign_or_marking("1.10", kind="marking") is not None

    def test_vmq_articles_in_db_bilingual_and_valid_chapters(self):
        db_path = os.getenv("DB_PATH", "master_database.sqlite")
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM vmq_articles").fetchone()[0]
            bilingual = cur.execute(
                "SELECT COUNT(*) FROM vmq_articles WHERE text_uz IS NOT NULL AND text_uz != '' AND text_ru IS NOT NULL AND text_ru != ''"
            ).fetchone()[0]
            dups = cur.execute(
                "SELECT clause_num, COUNT(*) FROM vmq_articles WHERE entry_type='clause' GROUP BY clause_num HAVING COUNT(*) > 1"
            ).fetchall()
            chapters = {r[0] for r in cur.execute("SELECT DISTINCT chapter_code FROM vmq_articles").fetchall()}

        assert total >= 500
        assert bilingual == total
        assert dups == []
        assert all(ch is not None and str(ch).strip() != "" for ch in chapters)


# ─── 3B: Corpus Quality & Remediation ───────────────────────────────────────

class TestWorkstream3B:
    def test_categories_realigned_no_41(self):
        db_path = os.getenv("DB_PATH", "master_database.sqlite")
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            has_41 = cur.execute("SELECT COUNT(*) FROM categories WHERE id = 41").fetchone()[0]
            total_cats = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
            cat9_count = cur.execute("SELECT COUNT(*) FROM canonical_questions WHERE category_id = 9").fetchone()[0]

        assert has_41 == 0
        assert total_cats >= 40
        assert cat9_count == 32

    def test_image_scenes_canonical_id_keys(self):
        scenes_path = "data/image_scenes.json"
        if not os.path.exists(scenes_path):
            pytest.skip("data/image_scenes.json not found")
        with open(scenes_path, "r", encoding="utf-8") as f:
            scenes = json.load(f)

        assert len(scenes) >= 782
        schemas = set()
        for k, entry in scenes.items():
            assert re.match(r"^(?:CANON-YHQ|CQ)-\d{4}$", k), f"Unexpected key {k}"
            assert entry.get("canonical_id") == k
            assert (entry.get("otish_tartibi_yoki_yechim") or "").strip(), f"Empty solution on {k}"
            assert (entry.get("yhq_qoidasi_va_asos") or "").strip(), f"Empty law rule on {k}"
            schemas.add(tuple(sorted(entry.keys())))
        assert len(schemas) == 1

    def test_canonical_bundle_integrity(self):
        bundle_path = "data/canonical_bundle.json"
        if not os.path.exists(bundle_path):
            pytest.skip("data/canonical_bundle.json not found")
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        assert bundle.get("canonical_count", 0) >= 1295
        assert bundle.get("db_catalog_revision", 0) >= 1
        assert bundle.get("payload_sha256")

    def test_remediated_class_a_cq_and_provenance(self):
        db_path = os.getenv("DB_PATH", "master_database.sqlite")
        checks = {
            "CANON-YHQ-0992": "A",
            "CANON-YHQ-1215": "B",
            "CANON-YHQ-1216": "E",
        }
        with get_db_connection(db_path) as conn:
            cur = conn.cursor()
            for cid, expected in checks.items():
                actual = str(cur.execute("SELECT correct_option_key FROM canonical_questions WHERE canonical_id = ?", (cid,)).fetchone()[0]).strip().upper()
                assert actual == expected
            cq1327 = cur.execute(
                "SELECT legal_verification_status, legal_doc_title FROM canonical_questions WHERE canonical_id = 'CQ-1327'"
            ).fetchone()
            assert cq1327[0] == "VERIFIED_PRIMARY_LAW"
            assert "975" in (cq1327[1] or "")
            empty_refs = cur.execute(
                "SELECT COUNT(*) FROM canonical_questions WHERE legal_reference IS NULL OR TRIM(legal_reference) = ''"
            ).fetchone()[0]
            assert empty_refs == 0


# ─── 3C: AI Ustoz 3.0 ────────────────────────────────────────────────────────

class TestWorkstream3C:
    def test_refund_rate_limit_usage_date_and_3tuple(self):
        from src.ai.gemini_service import GeminiService
        from src.bot.database import BotDatabase
        import inspect

        sig = inspect.signature(GeminiService.refund_rate_limit)
        assert "usage_date" in sig.parameters
        assert sig.parameters["usage_date"].default is None

        db = BotDatabase(os.getenv("DB_PATH"))
        uid = 99881122
        with db._get_connection() as conn:
            conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
            conn.commit()
        svc = GeminiService()
        allowed, current, max_l = svc.check_and_increment_rate_limit(uid, is_pro=True)
        assert allowed is True and current == 1 and max_l == 100
        svc.refund_rate_limit(uid, usage_date=svc._tashkent_today_str())
        with db._get_connection() as conn:
            rem = conn.execute(
                "SELECT request_count FROM ai_usage_limits WHERE user_id = ?", (uid,)
            ).fetchone()[0]
        assert rem == 0

    def test_true_sse_stream_with_thought_signature_and_4round_none(self, monkeypatch):
        """Tests :streamGenerateContent?alt=sse directly via mocked httpx.AsyncClient.stream."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_p3_true_sse_key")
        from src.ai.gemini_service import GeminiService
        from src.bot.database import BotDatabase

        db = BotDatabase(os.getenv("DB_PATH"))
        uid = 99882234
        with db._get_connection() as conn:
            conn.execute("UPDATE telegram_users SET is_pro = 1, subscription_expires_at = '2099-01-01' WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
            conn.commit()

        captured_payloads: List[Dict[str, Any]] = []

        class _FakeSSEResp:
            def __init__(self, lines: List[str]):
                self.status_code = 200
                self._lines = lines

            async def aread(self) -> bytes:
                return b""

            async def aiter_lines(self):
                for ln in self._lines:
                    yield ln

        @asynccontextmanager
        async def _fake_stream(self_client, method, url, json=None, headers=None, timeout=None):
            assert ":streamGenerateContent?alt=sse" in url
            captured_payloads.append(json)
            r_idx = len(captured_payloads)
            if r_idx <= 3:
                ev = {
                    "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 12, "thoughtsTokenCount": 8},
                    "candidates": [{
                        "content": {
                            "parts": [
                                {"text": "internal thought", "thought": True},
                                {"functionCall": {"name": "lookup_vmq_law", "args": {"clause_num": "78"}}, "thoughtSignature": f"sig_r{r_idx}"},
                            ]
                        }
                    }],
                }
                yield _FakeSSEResp([f"data: {__import__('json').dumps(ev)}"])
            else:
                ev1 = {
                    "usageMetadata": {"promptTokenCount": 80, "candidatesTokenCount": 25},
                    "candidates": [{"content": {"parts": [{"text": "hidden thought", "thought": True}, {"text": "Savol bo‘yicha VMQ 172 "}]} }],
                }
                ev2 = {
                    "candidates": [{"content": {"parts": [{"text": "78-bandiga ko‘ra 60 km/soat."}]}}],
                }
                yield _FakeSSEResp([
                    f"data: {__import__('json').dumps(ev1)}",
                    f"data: {__import__('json').dumps(ev2)}",
                    "data: [DONE]",
                ])

        client = TestClient(app)
        tok = generate_dev_init_data(user_id=uid)
        with patch("httpx.AsyncClient.stream", new=_fake_stream):
            with client.stream(
                "POST",
                "/api/ai/chat/stream",
                json={"message": "Aholi punktida tezlik?", "session_id": "sse_real_p3"},
                headers={"X-Telegram-Init-Data": tok},
            ) as resp:
                assert resp.status_code == 200
                raw_sse = "".join(resp.iter_text())

        events = [json.loads(line[6:]) for line in raw_sse.splitlines() if line.startswith("data: ")]
        types = [ev["type"] for ev in events]
        assert "status" in types and "delta" in types and "done" in types
        done_ev = next(ev for ev in events if ev["type"] == "done")
        assert done_ev["ok"] is True
        assert "internal thought" not in done_ev["reply"]
        assert "hidden thought" not in done_ev["reply"]
        assert "60 km/soat" in done_ev["reply"]

        # Verify 4 rounds total, round 2+ preserved thoughtSignature, and round 4 set toolConfig NONE
        assert len(captured_payloads) == 4
        r2_contents = captured_payloads[1]["contents"]
        model_parts = next(c["parts"] for c in r2_contents if c.get("role") == "model")
        assert any(p.get("thoughtSignature") == "sig_r1" for p in model_parts)
        assert captured_payloads[3]["toolConfig"]["functionCallingConfig"]["mode"] == "NONE"

    def test_midstream_cancelled_rollback(self, monkeypatch):
        """Client disconnect / CancelledError mid-stream must refund quota and purge orphan user row."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_p3_cancel_key")
        from src.ai.gemini_service import GeminiService
        from src.bot.database import BotDatabase

        db = BotDatabase(os.getenv("DB_PATH"))
        uid = 99883345
        with db._get_connection() as conn:
            conn.execute("UPDATE telegram_users SET is_pro = 1, subscription_expires_at = '2099-01-01' WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
            conn.commit()

        async def _slow_stream(self_inner, client, payload):
            yield ("delta", "Birinchi bo‘lak ")
            await asyncio.sleep(0.2)
            yield ("delta", "Ikkinchi bo‘lak")

        async def _run_cancel():
            svc = GeminiService()
            with patch.object(GeminiService, "_stream_gemini_with_fallback", new=_slow_stream):
                agen = svc.stream_chat(uid, "cancel_sess", "Test disconnect", is_pro=True, language="uz_latn")
                first = await agen.__anext__()  # status
                assert "status" in first
                second = await agen.__anext__()  # delta
                assert "delta" in second
                await agen.aclose()

        asyncio.run(_run_cancel())
        with db._get_connection() as conn:
            cnt_msgs = conn.execute("SELECT COUNT(*) FROM ai_conversations WHERE user_id = ?", (uid,)).fetchone()[0]
            cnt_quota = conn.execute("SELECT request_count FROM ai_usage_limits WHERE user_id = ?", (uid,)).fetchone()[0]
        assert cnt_msgs == 0
        assert cnt_quota == 0

    def test_sse_stream_empty_message_localized_error(self):
        client = TestClient(app)
        uid = 99883399
        tok = generate_dev_init_data(user_id=uid)
        with client.stream(
            "POST",
            "/api/ai/chat/stream",
            json={"message": "   ", "session_id": "empty_test", "language": "ru"},
            headers={"X-Telegram-Init-Data": tok},
        ) as resp:
            assert resp.status_code == 200
            raw_sse = "".join(resp.iter_text())
        events = [json.loads(line[6:]) for line in raw_sse.splitlines() if line.startswith("data: ")]
        assert events and events[0]["type"] == "error" and "введите" in events[0]["reply"]

    def test_sanitize_stream_piece_holdback_buffer(self):
        from src.ai.gemini_service import GeminiService

        safe1, buf1 = GeminiService._sanitize_stream_piece("", "Ushbu CANON", "uz_latn", flush=False)
        assert safe1 == "Ushbu "
        assert buf1 == "CANON"
        safe2, buf2 = GeminiService._sanitize_stream_piece(buf1, "-YHQ-0001 raqami.", "uz_latn", flush=True)
        assert "CANON-YHQ-0001" not in (safe1 + safe2)
        assert buf2 == ""

    def test_provenance_sql_caching_and_memory_skip(self):
        from src.ai.tools import get_provenance_select_sql

        db_path = os.getenv("DB_PATH", "master_database.sqlite")
        with get_db_connection(db_path) as conn:
            sql1 = get_provenance_select_sql(conn)
            sql2 = get_provenance_select_sql(conn)
            assert sql1 is sql2
            assert "cq.legal_verification_status" in sql1

        mem_conn = sqlite3.connect(":memory:")
        try:
            mem_sql = get_provenance_select_sql(mem_conn)
            assert "NULL AS legal_verification_status" in mem_sql
        finally:
            mem_conn.close()

    def test_apostrophe_normalization_lookup_and_is_resolved(self):
        from src.ai.tools import TOOL_MAPPING, tool_get_user_mistakes, tool_lookup_vmq_law, tool_search_questions
        from src.bot.database import BotDatabase

        for apos in ["\u02bb", "\u02bc", "\u2019", "'"]:
            res = tool_search_questions(f"to{apos}xtash", limit=2, language="uz_latn")
            assert isinstance(res, dict) and "questions" in res

        assert "lookup_vmq_law" in TOOL_MAPPING
        vmq_ch = tool_lookup_vmq_law(chapter_code="17-1", language="uz_latn")
        assert vmq_ch.get("count", 0) >= 1
        vmq_cl = tool_lookup_vmq_law(clause_num="78", language="uz_latn")
        assert vmq_cl.get("count", 0) >= 1 and "60" in json.dumps(vmq_cl, ensure_ascii=False)

        db = BotDatabase(os.getenv("DB_PATH"))
        uid = 99886678
        with db._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO telegram_users (user_id, username, first_name, language, created_at, last_active_at) VALUES (?, 'p3_mistake_tester', 'Tester', 'uz_latn', datetime('now'), datetime('now'))",
                (uid,),
            )
            conn.execute("DELETE FROM user_mistakes WHERE user_id = ?", (uid,))
            conn.execute(
                "INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, is_resolved, last_mistake_at) VALUES (?, 'CANON-YHQ-0001', 2, 1, datetime('now'))",
                (uid,),
            )
            conn.execute(
                "INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, is_resolved, last_mistake_at) VALUES (?, 'CANON-YHQ-0002', 3, 0, datetime('now'))",
                (uid,),
            )
            conn.commit()
        mres = tool_get_user_mistakes(uid, limit=5, language="uz_latn")
        cids = [m["canonical_id"] for m in mres.get("mistake_questions", [])]
        assert "CANON-YHQ-0002" in cids
        assert "CANON-YHQ-0001" not in cids

    def test_observability_snapshot_ai_metrics(self):
        from src.security.observability import observability

        observability.reset()
        observability.record_ai_invocation(
            streaming=True,
            ok=True,
            model_used="gemini-flash-lite-latest",
            ttft_ms=320.0,
            total_ms=1800.0,
            prompt_tokens=512,
            candidates_tokens=256,
            thoughts_tokens=0,
            estimated_cost_usd=0.00015,
            tools_called=["lookup_vmq_law"],
        )
        snap = observability.snapshot()
        ai = snap.get("ai_metrics", {})
        assert ai.get("calls_total") == 1
        assert ai.get("calls_streaming") == 1
        assert ai.get("prompt_tokens") == 512
        assert ai.get("tools_called", {}).get("lookup_vmq_law") == 1


# ─── 3D: Admin Editorial Workbench, Cards & Plans ───────────────────────────

class TestWorkstream3D:
    def test_editorial_ai_draft_upsert_sibling_autoclose_bulk_and_catalog(self, tmp_path, monkeypatch):
        import src.admin.auth_service as admin_auth
        import src.admin.routes_admin_questions as raq
        from src.db.provenance_classifier import bulk_approve_editorial_items_batched, submit_ai_draft

        iso_db = _copy_isolated_db(tmp_path, "editorial_3d.sqlite")
        monkeypatch.setattr(admin_auth, "DB_PATH", iso_db)
        monkeypatch.setattr(raq.sync_service, "db_path", iso_db)

        headers = _create_admin_headers(iso_db, "p3_ed_admin", "SUPERADMIN")
        client = TestClient(app)

        # Pick 2 pending items cleanly
        with get_db_connection(iso_db) as conn:
            rows = conn.execute(
                "SELECT id, canonical_id FROM editorial_review_queue WHERE review_status = 'PENDING_EDITORIAL_REVIEW' LIMIT 2"
            ).fetchall()
            assert len(rows) >= 2
            qid1, cid1 = int(rows[0][0]), str(rows[0][1])
            qid2, cid2 = int(rows[1][0]), str(rows[1][1])

            # Test upsert behavior on submit_ai_draft
            id_a = submit_ai_draft(conn, cid1, "uz_latn", "First draft", created_by="test")
            id_b = submit_ai_draft(conn, cid1, "uz_latn", "Updated draft", created_by="test")
            assert id_a == id_b

        # Call AI draft endpoint twice (3-lang JSON upsert, maxOutputTokens=1200)
        mock_ai = (
            {"candidates": [{"content": {"parts": [{"text": '{"uz_latn":"Lotin izoh","uz_cyrl":"Кирилл изоҳ","ru":"Русское пояснение"}'}]}}]},
            200,
            None,
        )
        with patch("src.ai.gemini_service.GeminiService._call_gemini_with_fallback", new=AsyncMock(return_value=mock_ai)), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "p3_ed_key"}):
            r_draft = client.post(f"/api/admin/questions/editorial/{qid1}/ai-draft", headers=headers)
            assert r_draft.status_code == 200
            assert r_draft.json()["drafts"]["ru"] == "Русское пояснение"

        # source_type + trilingual q search
        r_ai_list = client.get(
            "/api/admin/questions/editorial",
            params={"status": "AI_DRAFT_PENDING_REVIEW", "source_type": "AI_DRAFT", "q": cid1},
            headers=headers,
        )
        assert r_ai_list.status_code == 200
        assert r_ai_list.json()["total"] >= 1

        # Batched bulk approve cid1 -> auto-closes sibling AI_DRAFT_PENDING_REVIEW rows for cid1!
        with get_db_connection(iso_db) as conn:
            before_rev = conn.execute("SELECT CAST(value AS INTEGER) FROM system_settings WHERE key='catalog_version'").fetchone()[0]
            out = bulk_approve_editorial_items_batched(
                conn,
                queue_ids=[qid1],
                reviewer="p3_ed_admin",
                legal_verification_status="VERIFIED_PRIMARY_LAW",
                legal_doc_title="VMQ 172",
                legal_clause="78-band",
            )
            after_rev = conn.execute("SELECT CAST(value AS INTEGER) FROM system_settings WHERE key='catalog_version'").fetchone()[0]
            open_siblings = conn.execute(
                "SELECT COUNT(*) FROM editorial_review_queue WHERE canonical_id = ? AND review_status IN ('PENDING_EDITORIAL_REVIEW', 'AI_DRAFT_PENDING_REVIEW')",
                (cid1,),
            ).fetchone()[0]
        assert cid1 in out["approved"]
        assert after_rev == before_rev + 1
        assert open_siblings == 0

        # Bulk reject qid2
        r_rej = client.post(
            "/api/admin/questions/editorial/bulk-reject",
            json={"queue_ids": [qid2], "reason": "Test bulk reject"},
            headers=headers,
        )
        assert r_rej.status_code == 200
        assert qid2 in r_rej.json()["rejected"]

        # Catalog status & rebuild
        r_st = client.get("/api/admin/questions/catalog/status", headers=headers)
        assert r_st.status_code == 200
        assert r_st.json()["canonical_total"] >= 1295

        r_rb = client.post("/api/admin/questions/catalog/rebuild", headers=headers)
        assert r_rb.status_code == 200
        assert r_rb.json()["bundle"]["canonical_count"] >= 1295

        monkeypatch.undo()
        from src.api.routes_theory import invalidate_theory_caches
        invalidate_theory_caches(reload_engine=True)

    def test_admin_multi_card_and_plan_crud(self, tmp_path, monkeypatch):
        import src.admin.auth_service as admin_auth
        import src.admin.routes_admin_cards as rac
        import src.admin.routes_admin_plans as rap
        import src.payments.order_manager as om

        iso_db = _copy_isolated_db(tmp_path, "finance_3d.sqlite")
        monkeypatch.setattr(admin_auth, "DB_PATH", iso_db)
        monkeypatch.setattr(rac, "DB_PATH", iso_db)
        monkeypatch.setattr(rap, "DB_PATH", iso_db)
        monkeypatch.setattr(om, "DB_PATH", iso_db)
        om.invalidate_payment_cache()

        try:
            headers = _create_admin_headers(iso_db, "p3_fin_admin", "SUPERADMIN")
            client = TestClient(app)

            # Invalid card length rejected with 400
            bad_card = client.post(
                "/api/admin/cards",
                json={"cardholder_name": "TEST USER", "card_number": "1234", "card_type": "HUMO", "display_name": "Bad"},
                headers=headers,
            )
            assert bad_card.status_code == 400

            # Missing explicit card_id on PUT -> 404 (no silent fallback)
            missing_put = client.put(
                "/api/admin/cards/999999",
                json={"cardholder_name": "MISSING"},
                headers=headers,
            )
            assert missing_put.status_code == 404

            # Create valid second card & activate exclusively
            good_card = client.post(
                "/api/admin/cards",
                json={"cardholder_name": "SECOND HOLDER", "card_number": "8600123456789012", "card_type": "UZCARD", "display_name": "Reserve Uzcard", "is_monitoring": False},
                headers=headers,
            )
            assert good_card.status_code == 200
            new_cid = good_card.json()["card_id"]

            act = client.post(
                f"/api/admin/cards/{new_cid}/activate",
                json={"make_exclusive": True, "is_monitoring": True},
                headers=headers,
            )
            assert act.status_code == 200
            active_card = om.get_active_monitoring_card()
            assert active_card is not None and active_card["id"] == new_cid

            # Plan PUT with atomic price audit
            up_plan = client.put(
                "/api/admin/plans/pro_14",
                json={"base_price_uzs": 16000, "description": "Yangilangan 2 hafta", "display_order": 5, "reason": "Phase 3 test"},
                headers=headers,
            )
            assert up_plan.status_code == 200
            hist = client.get("/api/admin/plans/pro_14/price-history", headers=headers)
            assert hist.status_code == 200
            assert any(h["new_price_uzs"] == 16000 and h["reason"] == "Phase 3 test" for h in hist.json()["history"])
            active_plans = om.list_active_subscription_plans()
            pro14 = next(p for p in active_plans if p["id"] == "pro_14")
            assert pro14["description"] == "Yangilangan 2 hafta"
            assert pro14["display_order"] == 5
        finally:
            monkeypatch.undo()
            om.invalidate_payment_cache()


# ─── Offline AI Evaluation Harness ──────────────────────────────────────────

class TestOfflineAIEvaluation:
    """Evaluates grounding fidelity, fabricated-clause guardrail, ID sanitization & language purity."""

    def test_grounding_fidelity_and_guardrail_matrix(self):
        from src.ai.gemini_service import GeminiService

        svc = GeminiService()
        gt_unresolved = {"has_db_ground_truth": True, "legal_verification_status": "UNRESOLVED_LEGAL_REVIEW"}
        gt_verified = {"has_db_ground_truth": True, "legal_verification_status": "VERIFIED_PRIMARY_LAW"}

        # 1. Fabricated clause on unresolved item MUST be flagged in all 3 languages
        for lang_code in ("uz_latn", "uz_cyrl", "ru"):
            txt, meta = svc._post_process_reply("VMQ 172 ning 45-bandiga ko‘ra harakat qiling.", gt_unresolved, lang_code)
            assert meta["citation_flagged"] is True
            assert "⚠️" in txt

        # 2. Grounded VERIFIED_PRIMARY_LAW citation MUST NOT be flagged
        clean_txt, clean_meta = svc._post_process_reply("VMQ 172 78-bandiga ko‘ra 60 km/soat.", gt_verified, "uz_latn")
        assert clean_meta["citation_flagged"] is False
        assert "⚠️" not in clean_txt

        # 3. Internal IDs purged across formats
        scrubbed, _ = svc._post_process_reply(
            "CANON-YHQ-0045, CQ-1300 va UZ-YHQ-9911 asosida.", gt_verified, "uz_latn"
        )
        assert "CANON-YHQ" not in scrubbed and "CQ-1300" not in scrubbed and "UZ-YHQ" not in scrubbed

    def test_end_to_end_chat_grounding_and_language_purity(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "offline_eval_key")
        from src.ai.gemini_service import GeminiService
        from src.bot.database import BotDatabase

        db = BotDatabase(os.getenv("DB_PATH"))
        uid = 99991111
        with db._get_connection() as conn:
            conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
            conn.commit()

        svc = GeminiService()
        captured_req: Dict[str, Any] = {}

        async def _mock_call(self_inner, client, payload):
            captured_req["system"] = payload["system_instruction"]["parts"][0]["text"]
            return (
                {"candidates": [{"content": {"parts": [{"text": "Piyodalarga yo‘l bering, chorrahada ehtiyot bo‘ling."}]}}],
                 "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 40}},
                200,
                None,
            )

        with patch.object(GeminiService, "_call_gemini_with_fallback", new=_mock_call):
            result = asyncio.run(
                svc.chat(uid, "eval_gt", "Bu savolni tushuntiring", is_pro=True, language="uz_latn", canonical_id="CANON-YHQ-0001")
            )

        assert result["ok"] is True
        assert result["grounding"]["has_db_ground_truth"] is True
        assert "CANON-YHQ" not in captured_req.get("system", "") or "To'g'ri" in captured_req.get("system", "") or "Savol" in captured_req.get("system", "")
        cyr = len(re.findall(r"[\u0400-\u04FF]", result["reply"]))
        tot = max(1, len(re.findall(r"[a-zA-Z\u0400-\u04FF]", result["reply"])))
        assert cyr / tot < 0.25
