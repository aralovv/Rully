"""
Comprehensive Automated Test Suite for:
1. Admin Control Panel Authentication & Session Security (Argon2id, OTP, Session rotation, RBAC)
2. Telegram Humocardbot Notification Parsing (Exact Amount vs Account Balance differentiation)
3. Payment Order Lifecycle & Suffix Allocation Engine (1..999 UZS unique suffix)
4. Payment Matching Engine (Exact match, Duplicate idempotency, Late-payment review, Unmatched queue)
5. User Management & Manual Subscriptions (Block/Unblock, Grant 14/30d without fake revenue, Revoke)
6. Subscription Plans & Price History
7. Card Management (Fernet encryption at rest, Masked display)
8. User Activity Analytics & Retention (DAU/WAU/MAU, Classifications, Cohorts)
9. System Health & Financial Reconciliation
"""

import pytest
import sqlite3
import os
import time
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.security.crypto import (
    hash_password,
    verify_password,
    encrypt_data,
    decrypt_data,
    generate_secure_otp,
    hash_otp,
    verify_otp_hash,
    mask_card_number,
    generate_session_token
)
from src.payments.parser import parse_humocard_notification
from src.payments.order_manager import (
    create_or_get_payment_order,
    get_user_active_order,
    get_order_by_id,
    expire_stale_orders
)
from src.payments.matching_engine import process_incoming_payment_event
from src.analytics.tracker import (
    log_user_event,
    get_real_activity_analytics,
    classify_user_activity,
    get_retention_analytics
)
from src.admin.auth_service import (
    initiate_admin_login,
    verify_admin_otp,
    validate_admin_session,
    revoke_admin_session
)
from src.api.security import generate_dev_init_data

client = TestClient(app)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


@pytest.fixture(autouse=True, scope="module")
def cleanup_test_pollution():
    yield
    with sqlite3.connect(DB_PATH) as conn:
        real_ids = (1956239701, 8515329556, 8809526955)
        conn.execute("DELETE FROM payment_transactions")
        conn.execute("DELETE FROM payment_orders")
        conn.execute("DELETE FROM payment_events")
        conn.execute("DELETE FROM unmatched_payments")
        conn.execute("DELETE FROM payment_review_cases")
        conn.execute("DELETE FROM telegram_users WHERE user_id NOT IN (?, ?, ?)", real_ids)
        conn.execute("DELETE FROM user_subscriptions WHERE user_id NOT IN (?, ?, ?)", real_ids)
        conn.execute("DELETE FROM user_activity_events WHERE user_id NOT IN (?, ?, ?)", real_ids)
        conn.execute("DELETE FROM admin_audit_logs WHERE action IN ('PAYMENT_AUTO_MATCHED', 'LATE_PAYMENT_DETECTED', 'UNMATCHED_PAYMENT_LOGGED')")
        conn.commit()


# Helper to ensure a user exists in telegram_users
def ensure_test_user(user_id: int, username: str = "test_user"):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO telegram_users (user_id, username, first_name, is_pro, created_at, last_active_at)
            VALUES (?, ?, 'Test', 0, ?, ?)
        """, (user_id, username, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        conn.commit()


# Helper to create an authenticated admin session
def create_test_admin_session() -> str:
    session_token = generate_session_token()
    now_str = datetime.utcnow().isoformat()
    exp_str = (datetime.utcnow() + timedelta(hours=8)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM admin_users WHERE username = 'Anvarjon'")
        admin_id = c.fetchone()[0]
        c.execute("""
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', ?, ?, 0, ?)
        """, (session_token, admin_id, now_str, exp_str, now_str))
        conn.commit()
    return session_token


# -------------------------------------------------------------
# 1. Cryptographic Security & OTP Tests
# -------------------------------------------------------------
def test_crypto_argon2id_hashing():
    pwd = "AdminSecurePass2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, pwd) is True
    assert verify_password(hashed, "WrongPassword!") is False


def test_crypto_fernet_encryption():
    plain_card = "9860123456785370"
    encrypted = encrypt_data(plain_card)
    assert encrypted != plain_card
    decrypted = decrypt_data(encrypted)
    assert decrypted == plain_card


def test_crypto_otp_and_masking():
    otp = generate_secure_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()

    hashed_otp = hash_otp(otp)
    assert verify_otp_hash(otp, hashed_otp) is True
    assert verify_otp_hash("000000", hashed_otp) is False

    masked, suffix = mask_card_number("9860123456785370")
    assert masked == "9860 **** **** 5370"
    assert suffix == "5370"


# -------------------------------------------------------------
# 2. Humocardbot Notification Parsing Engine
# -------------------------------------------------------------
def test_humo_notification_parsing_exact_amount_vs_balance():
    # Real Humocardbot sample message with incoming amount AND final balance
    raw_text = (
        "🎉 To’ldirish\n"
        "➕ 14.347,00 UZS\n"
        "📍 HAMKORBANK PAYME AJ\n"
        "💳 HUMOCARD *5370\n"
        "🕓 00:05 15.11.2026\n"
        "💰 150.347,00 UZS"
    )

    parsed = parse_humocard_notification(raw_text)
    assert parsed is not None
    assert parsed["is_incoming"] is True
    # CRITICAL: Must parse 14347, NOT the 150347 balance!
    assert parsed["amount_uzs"] == 14347
    assert parsed["card_suffix"] == "5370"
    assert parsed["balance_uzs"] == 150347
    assert "PAYME" in parsed["payment_source"]


def test_humo_notification_parsing_invalid_messages():
    # Outgoing debit message (minus) must NOT be recognized as top-up
    debit_text = (
        "To’lov: Korzinka\n"
        "💳 HUMOCARD *5370\n"
        "➖ 45.000,00 UZS\n"
        "🕓 00:05 15.11.2026\n"
        "💰 105.347,00 UZS"
    )
    parsed = parse_humocard_notification(debit_text)
    assert parsed is not None
    assert parsed["is_incoming"] is False

    # Random text
    assert parse_humocard_notification("Salom, qandaysiz?") is None


# -------------------------------------------------------------
# 3. Order Lifecycle & Unique Suffix Engine
# -------------------------------------------------------------
def test_order_creation_and_suffix_allocation():
    test_user_id = 770000 + int(time.time() * 100) % 100000
    ensure_test_user(test_user_id, f"user_suffix_{test_user_id}")

    # Create first order for pro_14 (base price: 14,000 UZS)
    success, msg, order = create_or_get_payment_order(test_user_id, "pro_14")
    assert success is True
    assert order is not None
    assert order["plan_id"] == "pro_14"
    assert order["base_price_uzs"] == 14000
    assert 1 <= order["suffix_uzs"] <= 999
    assert order["final_amount_uzs"] == 14000 + order["suffix_uzs"]
    assert order["status"] == "PENDING"
    assert order["remaining_seconds"] > 800

    first_order_id = order["order_id"]
    first_amount = order["final_amount_uzs"]

    # Reopening SAME plan while unexpired must return the EXACT same active order
    success2, msg2, order2 = create_or_get_payment_order(test_user_id, "pro_14")
    assert success2 is True
    assert order2["order_id"] == first_order_id
    assert order2["final_amount_uzs"] == first_amount

    # Switching to DIFFERENT plan (pro_30) must expire old order and allocate new one
    success3, msg3, order3 = create_or_get_payment_order(test_user_id, "pro_30")
    assert success3 is True
    assert order3["order_id"] != first_order_id
    assert order3["plan_id"] == "pro_30"
    assert order3["base_price_uzs"] == 25000
    assert order3["final_amount_uzs"] == 25000 + order3["suffix_uzs"]

    # Verify old order is EXPIRED
    old_order = get_order_by_id(first_order_id)
    assert old_order["status"] == "EXPIRED"


# -------------------------------------------------------------
# 4. Payment Matching Engine & Financial Ledger
# -------------------------------------------------------------
def test_payment_matching_success_and_activation():
    test_user_id = 770002
    ensure_test_user(test_user_id, "user_match_test")

    success, _, order = create_or_get_payment_order(test_user_id, "pro_14")
    assert success is True
    exact_amount = order["final_amount_uzs"]
    order_id = order["order_id"]

    amount_str = f"{exact_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    msg_id = int(time.time() * 1000)

    # Simulate Humocardbot notification with the exact amount
    notif_text = (
        f"🎉 To’ldirish\n"
        f"➕ {amount_str} UZS\n"
        f"📍 HAMKORBANK PAYME AJ\n"
        f"💳 HUMOCARD *5370\n"
        f"🕓 00:05 18.11.2026\n"
        f"💰 200.000,00 UZS"
    )

    parsed = parse_humocard_notification(notif_text)
    assert parsed is not None

    res = asyncio.run(process_incoming_payment_event(
        parsed=parsed,
        source_chat="Humocardbot",
        message_id=msg_id
    ))

    assert res["status"] == "MATCHED"
    assert res["order_id"] == order_id
    assert res["user_id"] == test_user_id

    # Verify user subscription is active in DB
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (test_user_id,))
        row = c.fetchone()
        assert row is not None and row[0] == 1

        c.execute("SELECT * FROM payment_transactions WHERE order_id = ?", (order_id,))
        tx = c.fetchone()
        assert tx is not None

    # Idempotency / Deduplication test: re-processing identical notification should be ignored
    dup_res = asyncio.run(process_incoming_payment_event(
        parsed=parsed,
        source_chat="Humocardbot",
        message_id=msg_id
    ))
    assert dup_res["status"] == "DUPLICATE"


def test_payment_matching_unmatched_and_review():
    # 1. Unmatched payment: amount does not match any pending order
    unique_msg_id = int(time.time() * 1000) + 10
    now_min = datetime.utcnow().strftime("%H:%M")
    unmatched_text = (
        f"🎉 To’ldirish\n"
        f"➕ 99.888,00 UZS\n"
        f"📍 PAYME AJ\n"
        f"💳 HUMOCARD *5370\n"
        f"🕓 {now_min} 18.11.2026\n"
        f"💰 300.000,00 UZS"
    )
    parsed = parse_humocard_notification(unmatched_text)
    res = asyncio.run(process_incoming_payment_event(
        parsed=parsed,
        source_chat="Humocardbot",
        message_id=unique_msg_id
    ))
    assert res["status"] == "UNMATCHED"

    # 2. Late payment for EXPIRED order -> routed to PAYMENT_REVIEW
    test_user_id = 770003
    ensure_test_user(test_user_id, "user_late_test")

    _, _, order = create_or_get_payment_order(test_user_id, "pro_14")
    expired_order_id = order["order_id"]
    expired_amount = order["final_amount_uzs"]

    # Force order to EXPIRED in database
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE payment_orders SET status = 'EXPIRED' WHERE order_id = ?", (expired_order_id,))
        conn.commit()

    amount_str = f"{expired_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    late_msg_id = int(time.time() * 1000) + 20
    late_text = (
        f"🎉 To’ldirish\n"
        f"➕ {amount_str} UZS\n"
        f"📍 HAMKORBANK PAYME AJ\n"
        f"💳 HUMOCARD *5370\n"
        f"🕓 01:15 18.11.2026\n"
        f"💰 350.000,00 UZS"
    )

    late_parsed = parse_humocard_notification(late_text)
    late_res = asyncio.run(process_incoming_payment_event(
        parsed=late_parsed,
        source_chat="Humocardbot",
        message_id=late_msg_id
    ))
    assert late_res["status"] == "LATE_REVIEW"
    assert late_res["order_id"] == expired_order_id


# -------------------------------------------------------------
# 5. Admin Authentication & Session Management
# -------------------------------------------------------------
def test_admin_auth_flow():
    # Ensure fresh cookies for this test
    client.cookies.clear()

    # Step 1: Failed login with invalid password
    res_bad = client.post("/api/admin/auth/login", json={
        "username": "Anvarjon",
        "password": "WrongPassword123"
    })
    assert res_bad.status_code == 401

    # Step 2: Successful initiate login with valid credentials
    admin_pwd = os.getenv("ADMIN_PASSWORD", "test_admin_password_123")
    res_init = client.post("/api/admin/auth/login", json={
        "username": "Anvarjon",
        "password": admin_pwd
    })
    assert res_init.status_code == 200
    init_json = res_init.json()
    assert init_json["ok"] is True
    challenge_id = init_json["data"]["challenge_id"]

    # Read challenge directly from DB
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT otp_hash FROM admin_otp_challenges WHERE challenge_id = ?", (challenge_id,))
        row = c.fetchone()
        assert row is not None

    # Step 3: Wrong OTP check
    res_wrong_otp = client.post("/api/admin/auth/otp/verify", json={
        "challenge_id": challenge_id,
        "otp_code": "000000"
    })
    assert res_wrong_otp.status_code == 400

    # Step 4: Login via direct auth challenge update with known OTP
    otp_code = "789123"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE admin_otp_challenges SET otp_hash = ? WHERE challenge_id = ?", (hash_otp(otp_code), challenge_id))
        conn.commit()

    res_ok_otp = client.post("/api/admin/auth/otp/verify", json={
        "challenge_id": challenge_id,
        "otp_code": otp_code
    })
    assert res_ok_otp.status_code == 200
    auth_body = res_ok_otp.json()
    assert auth_body["ok"] is True
    session_token = auth_body["data"]["session_token"]
    assert len(session_token) > 20

    # Step 5: Access protected route with Bearer token
    headers = {"Authorization": f"Bearer {session_token}"}
    res_me = client.get("/api/admin/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["admin"]["username"] == "Anvarjon"

    # Step 6: Unauthorized access without token or cookies
    client.cookies.clear()
    res_unauth = client.get("/api/admin/auth/me")
    assert res_unauth.status_code == 401

    # Step 7: Logout / Revocation
    res_logout = client.post("/api/admin/auth/logout", headers=headers)
    assert res_logout.status_code == 200

    # Step 8: Token is now invalidated
    client.cookies.clear()
    res_revoked = client.get("/api/admin/auth/me", headers=headers)
    assert res_revoked.status_code == 401


# -------------------------------------------------------------
# 6. Admin User Management & Manual Subscriptions
# -------------------------------------------------------------
def test_admin_user_management():
    session_token = create_test_admin_session()
    headers = {"Authorization": f"Bearer {session_token}"}

    test_user_id = 880099
    ensure_test_user(test_user_id, "test_user_88")

    # 1. Search Users
    res_users = client.get(f"/api/admin/users?query=test_user_88", headers=headers)
    assert res_users.status_code == 200
    users_data = res_users.json()
    assert len(users_data["users"]) >= 1

    # 2. Block User
    res_block = client.post(f"/api/admin/users/{test_user_id}/block", json={"reason": "Spam faoliyat"}, headers=headers)
    assert res_block.status_code == 200

    # 3. Unblock User
    res_unblock = client.post(f"/api/admin/users/{test_user_id}/unblock", headers=headers)
    assert res_unblock.status_code == 200

    # 4. Grant Manual 14-day subscription (Price MUST be 0, status MANUAL_GRANT)
    res_grant14 = client.post(f"/api/admin/users/{test_user_id}/grant-subscription", json={
        "duration_days": 14,
        "reason": "Sovg'a"
    }, headers=headers)
    assert res_grant14.status_code == 200
    grant_data = res_grant14.json()
    assert grant_data["ok"] is True

    # Verify NO fake revenue was created
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (test_user_id,))
        assert c.fetchone()[0] == 1
        c.execute("SELECT price_uzs, status FROM user_subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user_id,))
        sub_row = c.fetchone()
        assert sub_row[0] == 0  # 0 UZS revenue
        assert sub_row[1] == "MANUAL_GRANT"

    # 5. Revoke Subscription
    res_revoke = client.post(f"/api/admin/users/{test_user_id}/revoke-subscription", json={
        "reason": "Qoidabuzarlik"
    }, headers=headers)
    assert res_revoke.status_code == 200

    # Verify user is no longer PRO
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (test_user_id,))
        assert c.fetchone()[0] == 0


# -------------------------------------------------------------
# 7. Subscription Plans & Pricing History
# -------------------------------------------------------------
def test_admin_subscription_plans_and_pricing():
    session_token = create_test_admin_session()
    headers = {"Authorization": f"Bearer {session_token}"}

    # 1. Get plans
    res_plans = client.get("/api/admin/plans", headers=headers)
    assert res_plans.status_code == 200
    plans = res_plans.json()["plans"]
    assert len(plans) >= 2

    # 2. Update price for pro_14 with audit reason
    res_update = client.post("/api/admin/plans/pro_14/price", json={
        "new_price_uzs": 16000,
        "reason": "Yillik narx indeksatsiyasi"
    }, headers=headers)
    assert res_update.status_code == 200

    # Verify price history entry was recorded
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT old_price_uzs, new_price_uzs, reason FROM subscription_price_history WHERE plan_id = 'pro_14' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        assert row is not None
        assert row[1] == 16000
        assert row[2] == "Yillik narx indeksatsiyasi"

    # Restore price back to 14000 for consistency
    client.post("/api/admin/plans/pro_14/price", json={
        "new_price_uzs": 14000,
        "reason": "Test qaytarish"
    }, headers=headers)


# -------------------------------------------------------------
# 8. User Activity Analytics & Retention Cohorts
# -------------------------------------------------------------
def test_analytics_metrics_and_classifications():
    test_user_id = 998877
    ensure_test_user(test_user_id, "user_analytics_test")

    # Log multiple sample user activity events
    log_user_event(test_user_id, "BOT_START")
    log_user_event(test_user_id, "SESSION_START")
    log_user_event(test_user_id, "EXAM_FINISHED", {"score": 19, "passed": True})

    # 1. Activity classification
    classification = classify_user_activity(test_user_id)
    assert classification["category"] in ["Highly Active", "Active", "Occasionally Active", "At Risk", "Inactive"]
    assert "explanation" in classification

    # 2. Daily / Weekly / Monthly metrics
    metrics = get_real_activity_analytics()
    assert "dau" in metrics
    assert "wau" in metrics
    assert "mau" in metrics
    assert "engagement_ratio_pct" in metrics
    assert metrics["dau"] >= 1

    # 3. Retention Cohorts
    retention_data = get_retention_analytics()
    assert "cohorts" in retention_data


# -------------------------------------------------------------
# 9. Admin Overview Dashboard & Financial Reconciliation
# -------------------------------------------------------------
def test_admin_dashboard_and_reconciliation():
    session_token = create_test_admin_session()
    headers = {"Authorization": f"Bearer {session_token}"}

    # 1. Dashboard Overview KPIs
    res_dash = client.get("/api/admin/dashboard/kpi", headers=headers)
    assert res_dash.status_code == 200
    kpis = res_dash.json()["kpis"]
    assert "total_users" in kpis
    assert "active_subscribers" in kpis
    assert "today_revenue_uzs" in kpis
    assert "total_successful_payments" in kpis

    # 2. Sales Analytics with Filter
    res_sales = client.get("/api/admin/dashboard/sales-analytics?range_filter=30d", headers=headers)
    assert res_sales.status_code == 200
    sales_data = res_sales.json()
    assert "daily_chart" in sales_data
    assert "summary" in sales_data

    # 3. Financial Reconciliation Report
    res_recon = client.get("/api/admin/payments/reconciliation", headers=headers)
    assert res_recon.status_code == 200
    recon_json = res_recon.json()
    assert "is_balanced" in recon_json
    assert "ledger_summary" in recon_json
    assert "events_summary" in recon_json


# -------------------------------------------------------------
# 10. User Mini App Payment Endpoints
# -------------------------------------------------------------
def test_miniapp_user_payment_endpoints():
    init_data = generate_dev_init_data(user_id=8809526955)

    # 1. Create order
    res_create = client.post(
        "/api/payment/orders/create",
        json={"plan_id": "pro_14"},
        headers={"X-Telegram-Init-Data": init_data}
    )
    assert res_create.status_code == 200
    order_info = res_create.json()["order"]
    order_id = order_info["order_id"]
    assert order_info["plan_id"] == "pro_14"
    assert "card_number_masked" in order_info

    # 2. Check active order
    res_active = client.get(
        "/api/payment/orders/active",
        headers={"X-Telegram-Init-Data": init_data}
    )
    assert res_active.status_code == 200
    assert res_active.json()["has_active_order"] is True

    # 3. Check order status polling
    res_status = client.get(
        f"/api/payment/orders/{order_id}/status",
        headers={"X-Telegram-Init-Data": init_data}
    )
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "PENDING"
    assert res_status.json()["is_paid"] is False


# -------------------------------------------------------------
# 11. In-Bot Invoice & Congratulations Formatting
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_inbot_notifications_formatting():
    from unittest.mock import patch
    from src.security.telegram_notifier import (
        send_payment_invoice_to_user,
        send_user_payment_success_notification,
        send_user_subscription_granted_notification
    )

    with patch("src.security.telegram_notifier.send_telegram_message") as mock_send:
        mock_send.return_value = True

        # 1. Invoice notification contains Order Code
        await send_payment_invoice_to_user(
            user_id=8809526955,
            plan_name="14 kunlik PRO",
            cardholder_name="ANVARJON ARALOV",
            card_number_full="9860160148225370",
            final_amount_uzs=14321,
            order_id="ORD-20261118-TEST1"
        )
        assert mock_send.called
        sent_text = mock_send.call_args[0][2]
        assert "Buyurtma kodi: <code>ORD-20261118-TEST1</code>" in sent_text
        assert "9860 1601 4822 5370" in sent_text
        assert "14 321" in sent_text

        # 2. Payment success congratulations notification
        await send_user_payment_success_notification(
            user_id=8809526955,
            plan_name="14 kunlik PRO",
            expires_at="2026-12-02 12:00:00",
            duration_days=14
        )
        sent_congrats = mock_send.call_args[0][2]
        assert sent_congrats.startswith("🎉 Tabriklaymiz!")
        assert "PRO obuna" in sent_congrats

        # 3. Admin-granted subscription congratulations notification
        await send_user_subscription_granted_notification(
            user_id=8809526955,
            duration_days=30,
            expires_at="2026-12-18 12:00:00"
        )
        sent_granted = mock_send.call_args[0][2]
        assert sent_granted.startswith("🎉 Tabriklaymiz!")
        assert "+30 kunlik PRO obuna" in sent_granted


# -------------------------------------------------------------
# 12. Order Timer & Expiration Lifecycle
# -------------------------------------------------------------
def test_order_timer_and_expiration_lifecycle():
    init_data = generate_dev_init_data(user_id=8809526955)

    # 1. Create a fresh order
    res_create = client.post(
        "/api/payment/orders/create",
        json={"plan_id": "pro_14"},
        headers={"X-Telegram-Init-Data": init_data}
    )
    assert res_create.status_code == 200
    order_data = res_create.json()["order"]
    order_id = order_data["order_id"]
    assert order_data["remaining_seconds"] > 800  # ~900s for 15 mins

    # 2. Status initially pending
    order_now = get_order_by_id(order_id)
    assert order_now["status"] == "PENDING"
    assert order_now["remaining_seconds"] > 0

    # 3. Fast-forward expiration into the past
    past_iso = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE payment_orders SET expires_at = ? WHERE order_id = ?", (past_iso, order_id))

    # 4. Querying get_order_by_id immediately triggers expiration transition
    expired_order = get_order_by_id(order_id)
    assert expired_order["status"] == "EXPIRED"
    assert expired_order["remaining_seconds"] == 0

    # 5. Polling endpoint detects is_expired
    res_poll = client.get(
        f"/api/payment/orders/{order_id}/status",
        headers={"X-Telegram-Init-Data": init_data}
    )
    assert res_poll.status_code == 200
    res_json = res_poll.json()
    assert res_json["status"] == "EXPIRED"
    assert res_json["is_expired"] is True
    assert res_json["remaining_seconds"] == 0

    # 6. Active order check returns none
    active_check = get_user_active_order(8809526955)
    assert active_check is None


# -------------------------------------------------------------
# 13. Admin Broadcast System
# -------------------------------------------------------------
def test_admin_broadcast_system():
    admin_session = create_test_admin_session()
    headers = {"Authorization": f"Bearer {admin_session}"}

    # 1. Check audience segments
    res_aud = client.get("/api/admin/broadcast/audience", headers=headers)
    assert res_aud.status_code == 200
    aud_json = res_aud.json()
    assert aud_json["ok"] is True
    assert "counts" in aud_json
    assert aud_json["counts"]["all"] >= 1

    # 2. Dispatch broadcast (mocked delivery)
    from unittest.mock import patch
    with patch("src.admin.routes_admin_broadcast.send_telegram_message") as mock_send:
        mock_send.return_value = True

        res_send = client.post(
            "/api/admin/broadcast",
            json={
                "message_text": "<b>Hurmatli foydalanuvchilar!</b> Tizim muvaffaqiyatli yangilandi.",
                "target_group": "all"
            },
            headers=headers
        )
        assert res_send.status_code == 200
        send_json = res_send.json()
        assert send_json["ok"] is True
        assert send_json["sent_count"] >= 1
        assert send_json["failed_count"] == 0

    # 3. Check broadcast history audit log
    res_hist = client.get("/api/admin/broadcast/history", headers=headers)
    assert res_hist.status_code == 200
    hist_json = res_hist.json()
    assert hist_json["ok"] is True
    assert len(hist_json["history"]) >= 1
    latest = hist_json["history"][0]
    assert latest["action"] == "BROADCAST_SENT"
    assert "Tizim muvaffaqiyatli yangilandi" in latest["meta"]["message_snippet"]

