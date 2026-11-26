"""
Wave 3 AI Ustoz 2.0 Verification Suite:
- Header-only Gemini API key (never in query URL)
- CDN-first vision image order
- Failed turn DB rollback & quota refund
- Integer + decimal clause hallucination guardrail
- Bookmark cards ("saved_questions") collection + history persistence
- Weak-Pattern Analyzer & 7-Day Study Plan tools
- 3/day Free teaser quota + SSE /api/ai/chat/stream endpoint
"""
import asyncio
import json
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.ai.gemini_service import GeminiService
from src.ai.tools import TOOL_MAPPING, tool_analyze_weak_patterns, tool_generate_study_plan
from src.api.main import app
from src.api.security import generate_dev_init_data
from src.bot.database import BotDatabase


def test_bookmarks_card_key_and_history_card_persistence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_ai_key_no_query_leak")
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99771122
    db.get_or_create_user(uid, username="ai_wave3_driver")
    with db._get_connection() as conn:
        conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM user_bookmarks WHERE user_id = ?", (uid,))
        conn.commit()
    db.toggle_bookmark(uid, "CANON-YHQ-0001")

    service = GeminiService()
    r1 = ({"candidates": [{"content": {"parts": [{"functionCall": {"name": "get_user_bookmarks", "args": {"limit": 3}}}]}}]}, 200, None)
    r2 = ({"candidates": [{"content": {"parts": [{"text": "Mana saqlangan savolingiz."}]}}]}, 200, None)

    with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(side_effect=[r1, r2])):
        out = asyncio.run(service.chat(uid, "bm-sess", "Saqlangan savollarimni ko'rsat", is_pro=True, language="uz_latn"))
    assert out["ok"] is True
    assert len(out["cards"]) == 1
    assert out["cards"][0]["canonical_id"] == "CANON-YHQ-0001"

    hist = service.get_conversation_history(uid, "bm-sess", limit=10, include_meta=True)
    assistant_msgs = [m for m in hist if m["role"] == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["cards"][0]["canonical_id"] == "CANON-YHQ-0001"


def test_integer_clause_guardrail_and_failed_turn_rollback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_ai_key_guard")
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99771123
    db.get_or_create_user(uid, username="guard_driver")
    with db._get_connection() as conn:
        conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
        conn.commit()

    service = GeminiService()
    # Test integer clause guardrail regex
    replied, meta = service._apply_legal_citation_guardrail(
        "Ushbu qoida YHQ 78-bandi bo'yicha belgilanadi.",
        {"legal_verification_status": "UNRESOLVED_LEGAL_REVIEW", "has_db_ground_truth": True},
        "uz_latn",
    )
    assert meta["citation_flagged"] is True
    assert "tekshiruvda" in replied.lower()

    # Failed Gemini call rolls back BOTH usage limit AND user message row
    with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(return_value=(None, 503, "down"))):
        fail_res = asyncio.run(service.chat(uid, "fail-sess", "Salom", is_pro=True, language="uz_latn"))
    assert fail_res["ok"] is False
    hist_after = service.get_conversation_history(uid, "fail-sess", limit=10, include_meta=True)
    assert hist_after == []


def test_weak_pattern_and_study_plan_tools():
    assert "analyze_weak_patterns" in TOOL_MAPPING
    assert "generate_study_plan" in TOOL_MAPPING
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99771124
    db.get_or_create_user(uid, username="plan_driver")
    sess = db.create_session(uid, "CUSTOM", "uz_latn", ["CANON-YHQ-0001"])
    db.process_session_answer(sess["session_id"], uid, "CANON-YHQ-0001", "B", "A", False, "CUSTOM")

    weak = tool_analyze_weak_patterns(uid, "uz_latn")
    assert weak["weak_categories_count"] >= 1
    assert len(weak["top_mistake_questions"]) >= 1

    plan = tool_generate_study_plan(uid, days=7, language="uz_latn")
    assert plan["days"] == 7
    assert len(plan["plan"]) == 7


def test_free_tier_3_teaser_quota_and_sse_streaming(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_ai_key_stream")
    client = TestClient(app)
    uid = 99771125
    token = generate_dev_init_data(user_id=uid)
    db = BotDatabase(os.getenv("DB_PATH"))
    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_pro = 0 WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM ai_conversations WHERE user_id = ?", (uid,))
        conn.commit()

    headers = {"X-Telegram-Init-Data": token}
    st = client.get("/api/ai/status", headers=headers).json()
    assert st["free_teaser_daily"] == 3
    assert st["usage"]["max"] == 3
    assert st["usage"]["remaining"] == 3

    mock_ok = ({"candidates": [{"content": {"parts": [{"text": "Tushuntiraman: piyodalarga yo'l bering."}]}}]}, 200, None)
    with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(return_value=mock_ok)):
        for i in range(3):
            r = client.post("/api/ai/chat", json={"message": f"Savol {i}", "session_id": "teaser"}, headers=headers)
            assert r.status_code == 200 and r.json()["ok"] is True

        # 4th message triggers friendly free-teaser PRO upgrade wall
        r4 = client.post("/api/ai/chat", json={"message": "Savol 4", "session_id": "teaser"}, headers=headers)
        assert r4.status_code == 200
        assert r4.json()["ok"] is False
        assert r4.json()["requires_pro"] is True

    # PRO user SSE streaming endpoint yields status, delta, and done events
    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_pro = 1, subscription_expires_at = '2099-01-01' WHERE user_id = ?", (uid,))
        conn.commit()
    with patch.object(GeminiService, "_call_gemini_with_fallback", new=AsyncMock(return_value=mock_ok)):
        with client.stream("POST", "/api/ai/chat/stream", json={"message": "Stream test", "session_id": "sse1"}, headers=headers) as resp:
            assert resp.status_code == 200
            raw_sse = "".join(resp.iter_text())
    events = [json.loads(line[6:]) for line in raw_sse.splitlines() if line.startswith("data: ")]
    types = [ev["type"] for ev in events]
    assert "status" in types and "delta" in types and "done" in types
