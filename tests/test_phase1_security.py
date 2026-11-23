import os
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.security import generate_dev_init_data
from src.security.rate_limiter import rate_limiter

client = TestClient(app)

def test_render_backdoor_fail_closed(monkeypatch):
    """Criterion 1.1: Render or production cloud environment strictly forbids manual activation."""
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("ALLOW_TEST_ACTIVATION", "true")
    token = generate_dev_init_data(user_id=12345678)
    
    resp = client.post(
        "/api/subscription/activate",
        json={"plan_id": "pro_14"},
        headers={"X-Telegram-Init-Data": token}
    )
    assert resp.status_code == 403
    assert "DIRECT_ACTIVATION_DISABLED" in resp.json()["detail"]

def test_session_idor_protection():
    """Criterion 1.2: User A cannot read, answer, or finish User B's session."""
    user_a_token = generate_dev_init_data(user_id=11111111)
    user_b_token = generate_dev_init_data(user_id=22222222)

    # 1. User B starts a session
    start_resp = client.post(
        "/api/session/start",
        json={"session_type": "RANDOM", "total_questions": 10},
        headers={"X-Telegram-Init-Data": user_b_token}
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]
    first_q = start_resp.json()["questions"][0]["canonical_id"]

    # 2. User A tries to GET User B's session
    get_resp = client.get(
        f"/api/session/{session_id}",
        headers={"X-Telegram-Init-Data": user_a_token}
    )
    assert get_resp.status_code == 403
    assert "Forbidden" in get_resp.json()["detail"]

    # 3. User A tries to POST answer to User B's session
    ans_resp = client.post(
        "/api/session/answer",
        json={"session_id": session_id, "canonical_id": first_q, "selected_key": "A"},
        headers={"X-Telegram-Init-Data": user_a_token}
    )
    assert ans_resp.status_code == 403
    assert "Forbidden" in ans_resp.json()["detail"]

    # 4. User A tries to POST finish to User B's session
    fin_resp = client.post(
        "/api/session/finish",
        json={"session_id": session_id, "time_elapsed_seconds": 12.0},
        headers={"X-Telegram-Init-Data": user_a_token}
    )
    assert fin_resp.status_code == 403
    assert "Forbidden" in fin_resp.json()["detail"]

def test_cors_policy_strict_protection():
    """Criterion 1.3: Untrusted origins receive NO Access-Control-Allow-Origin header."""
    evil_resp = client.options(
        "/api/categories",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert "access-control-allow-origin" not in evil_resp.headers

    # Trusted origin receives header
    trusted_resp = client.options(
        "/api/categories",
        headers={
            "Origin": "https://rully-three.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert trusted_resp.headers.get("access-control-allow-origin") == "https://rully-three.vercel.app"

def test_admin_cookie_secure_in_production(monkeypatch):
    """Criterion 1.4: Cookie has Secure flag in cloud/HTTPS production."""
    monkeypatch.setenv("VERCEL", "1")
    from src.admin.auth_service import initiate_admin_login, _get_connection
    from src.security.crypto import hash_otp

    # Create dummy admin challenge
    challenge_id = "test-challenge-123"
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO admin_otp_challenges (
                challenge_id, admin_id, otp_hash, telegram_id, attempts_count, max_attempts, is_used, created_at, expires_at
            ) VALUES (?, 1, ?, 1956239701, 0, 5, 0, datetime('now'), datetime('now', '+5 minutes'))
        """, (challenge_id, hash_otp("123456")))
        conn.commit()

    resp = client.post(
        "/api/admin/auth/otp/verify",
        json={"challenge_id": challenge_id, "otp_code": "123456"}
    )
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "admin_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()

def test_telegram_webhook_secret_fail_closed(monkeypatch):
    """Criterion 1.5: Missing or invalid secret token returns 403."""
    # 1. No secret configured in env
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    resp = client.post(
        "/api/telegram-webhook",
        json={"update_id": 12345},
        headers={"X-Telegram-Bot-Api-Secret-Token": "some-secret"}
    )
    assert resp.status_code == 403

    # 2. Secret configured, but invalid token supplied
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super-secret-token")
    resp_invalid = client.post(
        "/api/telegram-webhook",
        json={"update_id": 12345},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-token"}
    )
    assert resp_invalid.status_code == 403

def test_api_rate_limiting(monkeypatch):
    """Criterion 1.6: Endpoints enforce sliding window rate limiting."""
    monkeypatch.setenv("ENABLE_TEST_RATE_LIMIT", "true")
    rate_limiter.reset()

    user_token = generate_dev_init_data(user_id=77777777)

    # 1. Session start: max 10 / min
    for _ in range(10):
        r = client.post(
            "/api/session/start",
            json={"session_type": "RANDOM", "total_questions": 10},
            headers={"X-Telegram-Init-Data": user_token}
        )
        assert r.status_code == 200
    r_blocked = client.post(
        "/api/session/start",
        json={"session_type": "RANDOM", "total_questions": 10},
        headers={"X-Telegram-Init-Data": user_token}
    )
    assert r_blocked.status_code == 429
    assert "Too many session start requests" in r_blocked.json()["detail"]

    # 2. Order creation: max 3 / min
    rate_limiter.reset()
    for _ in range(3):
        r = client.post(
            "/api/payment/orders/create",
            json={"plan_id": "pro_14"},
            headers={"X-Telegram-Init-Data": user_token}
        )
        assert r.status_code == 200
    r_order_blocked = client.post(
        "/api/payment/orders/create",
        json={"plan_id": "pro_14"},
        headers={"X-Telegram-Init-Data": user_token}
    )
    assert r_order_blocked.status_code == 429
