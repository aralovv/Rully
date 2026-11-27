"""
Phase 4 (P3) Verification Tests:
1. Cache-Control & Edge CDN headers.
2. Script defer tags in static/index.html.
3. AI Assistant quota refund on API failure or error.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.ai.gemini_service import GeminiService
from src.db_adapter import get_db_connection

client = TestClient(app)

def test_cache_control_headers():
    # 1. Root / index.html should have revalidation headers
    resp = client.get("/")
    assert resp.status_code == 200
    cc = resp.headers.get("Cache-Control", "")
    assert "max-age=0" in cc or "must-revalidate" in cc

    # 2. Categories API depends on authenticated user language -> MUST NOT use shared s-maxage CDN caching
    resp_cat = client.get("/api/categories")
    assert resp_cat.status_code == 200
    cc_cat = resp_cat.headers.get("Cache-Control", "")
    assert "private" in cc_cat and "no-store" in cc_cat
    assert "s-maxage" not in cc_cat

    # 3. Practical modules contains user progress -> MUST NOT be public/s-maxage cached
    resp_amaliy = client.get("/api/amaliy/modules")
    cc_amaliy = resp_amaliy.headers.get("Cache-Control", "")
    assert "private" in cc_amaliy or "no-cache" in cc_amaliy
    assert "s-maxage" not in cc_amaliy


def test_script_tags_have_defer_in_index_html():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Verify that core application scripts have defer attribute
    for script_name in ["icons.js", "translations.js", "cheatsheet_data.js", "app.js"]:
        tag = f'script defer src="/static/js/{script_name}'
        assert tag in html, f"Script {script_name} must have defer attribute to prevent DOM blocking"


def test_ai_rate_limit_refund():
    service = GeminiService()
    test_user_id = 999777

    # Ensure clean slate
    with get_db_connection() as conn:
        conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (test_user_id,))
        conn.commit()

    # Increment rate limit
    allowed, count, max_l = service.check_and_increment_rate_limit(test_user_id, is_pro=True)
    assert allowed is True
    assert count == 1

    # Check in DB (uses unified Tashkent UTC+5 usage_date)
    today = service._tashkent_today_str()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT request_count FROM ai_usage_limits WHERE user_id = ? AND usage_date = ?", (test_user_id, today))
        row = c.fetchone()
        assert row["request_count"] == 1

    # Refund rate limit
    service.refund_rate_limit(test_user_id)

    # Check refund reflected in DB
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT request_count FROM ai_usage_limits WHERE user_id = ? AND usage_date = ?", (test_user_id, today))
        row = c.fetchone()
        assert row["request_count"] == 0

    # Cleanup
    with get_db_connection() as conn:
        conn.execute("DELETE FROM ai_usage_limits WHERE user_id = ?", (test_user_id,))
        conn.commit()
