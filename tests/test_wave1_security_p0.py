"""
Wave 1 P0 Security, Isolation, Leak & Correctness Regression Suite.
"""
import os
import pytest
from fastapi.testclient import TestClient

from src.api.main import app, create_app
from src.api.deps import get_db, invalidate_user_cache
from src.api.security import generate_dev_init_data
from src.bot.database import BotDatabase
from src.security.crypto import decrypt_data, encrypt_data, hash_otp, verify_otp_hash, _get_secret_key
from src.security.rate_limiter import get_client_ip


def test_pytest_runs_on_isolated_temp_database():
    """Verify tests NEVER mutate repository master_database.sqlite directly."""
    active_db = os.path.abspath(os.getenv("DB_PATH", "master_database.sqlite"))
    repo_master = os.path.abspath("master_database.sqlite")
    assert active_db != repo_master, "Tests must run against isolated temporary DB copy"


def test_crypto_fail_closed_and_keyed_otp(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test_secret_alpha_12345")
    ct = encrypt_data("8600123412345678")
    assert decrypt_data(ct) == "8600123412345678"

    # Legacy plain digits allowed, but invalid ENC:/Fernet ciphertext must raise ValueError
    assert decrypt_data("8600123412345678") == "8600123412345678"
    with pytest.raises(ValueError):
        decrypt_data("ENC:corrupted_secret")
    with pytest.raises(ValueError):
        decrypt_data("gAAAAA_invalid_ciphertext")

    # Keyed HMAC OTP verification changes when SECRET_KEY rotates
    otp_h1 = hash_otp("654321")
    assert verify_otp_hash("654321", otp_h1) is True
    monkeypatch.setenv("SECRET_KEY", "rotated_secret_beta_999")
    assert verify_otp_hash("654321", otp_h1) is False

    # Fail closed in non-test production mode when SECRET_KEY is unset
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError):
        _get_secret_key()


def test_trusted_proxy_ip_extraction():
    class _Req:
        def __init__(self, headers, host):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    # Untrusted direct public peer CANNOT spoof forwarding headers
    assert get_client_ip(_Req({"cf-connecting-ip": "1.2.3.4", "x-forwarded-for": "5.6.7.8"}, "198.51.100.44")) == "198.51.100.44"
    # Trusted proxy peer honors rightmost untrusted IP in XFF chain
    assert get_client_ip(_Req({"x-forwarded-for": "1.2.3.4, 203.0.113.88, 10.0.0.5"}, "10.0.0.1")) == "203.0.113.88"


def test_exam_mode_never_leaks_answers_and_blocked_user_rejected():
    client = TestClient(app)
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99441122
    token = generate_dev_init_data(user_id=uid)

    # Ensure unblocked user can start exam, and answers are NOT leaked
    with db._get_connection() as conn:
        conn.execute("DELETE FROM exam_results WHERE user_id = ?", (uid,))
        conn.execute("UPDATE telegram_users SET is_blocked = 0 WHERE user_id = ?", (uid,))
        conn.commit()
    invalidate_user_cache(uid)

    exam_res = client.post(
        "/api/session/start",
        json={"session_type": "EXAM", "total_questions": 20, "language": "uz_latn"},
        headers={"X-Telegram-Init-Data": token},
    )
    assert exam_res.status_code == 200
    questions = exam_res.json()["questions"]
    assert len(questions) == 20
    assert all(q.get("correct_option_key") is None for q in questions), "EXAM mode leaked answer keys!"
    assert all(q.get("explanation") is None for q in questions), "EXAM mode leaked explanations!"

    # Blocking user immediately revokes both /api/auth/telegram and /api/user/me
    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_blocked = 1 WHERE user_id = ?", (uid,))
        conn.commit()
    invalidate_user_cache(uid)

    me_blocked = client.get("/api/user/me", headers={"X-Telegram-Init-Data": token})
    assert me_blocked.status_code == 403
    assert "USER_BLOCKED" in me_blocked.text

    auth_blocked = client.post("/api/auth/telegram", json={"init_data": token})
    assert auth_blocked.status_code == 403
    assert "USER_BLOCKED" in auth_blocked.text


def test_webhook_info_requires_admin_and_ping_hides_key_length(monkeypatch):
    client = TestClient(app)
    unauth = client.get("/api/telegram-webhook/info")
    assert unauth.status_code == 401

    ping = client.get("/api/ping")
    assert ping.status_code == 200
    assert "gemini_key_len" not in ping.json()


def test_cors_blocks_lookalike_vercel_subdomain_in_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VERCEL", "1")
    prod_app = create_app(public_only=True)
    prod_client = TestClient(prod_app)

    evil = prod_client.options(
        "/api/categories",
        headers={"Origin": "https://rully-phishing-clone.vercel.app", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in evil.headers

    good = prod_client.options(
        "/api/categories",
        headers={"Origin": "https://rully-three.vercel.app", "Access-Control-Request-Method": "GET"},
    )
    assert good.headers.get("access-control-allow-origin") == "https://rully-three.vercel.app"
