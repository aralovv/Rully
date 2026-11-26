"""
Native Telegram Stars (XTR) End-to-End Test Suite:
- Invoice creation via POST /api/payment/stars/invoice (currency="XTR", provider_token="")
- Ownership & status polling via GET /api/payment/stars/{order_id}/status
- Strict pre_checkout_query security checks (amount tampering, user mismatch, currency)
- Atomic & idempotent PRO activation + additive duration extension on replay/repeat purchase
- Telegram Bot /pro command, buy_stars callback send_invoice, and F.successful_payment handler
- Admin KPI, /api/admin/payments/stars, and balanced HUMO+Stars reconciliation parity
- Mini App profile.js openInvoice + trilingual i18n parity
"""

import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.api.deps import invalidate_user_cache
from src.api.main import app
from src.api.security import generate_dev_init_data
from src.bot.database import BotDatabase
from src.bot.handlers.payments import (
    cb_buy_with_telegram_stars,
    handle_stars_pre_checkout,
    handle_stars_successful_payment,
)
from src.bot.handlers.start import cmd_subscription
from src.payments.stars_service import (
    create_stars_invoice_order,
    fulfill_stars_payment,
    validate_stars_pre_checkout,
)
from src.security.crypto import hash_password

ROOT_DIR = Path(__file__).resolve().parent.parent


def _ensure_admin_token(username: str, role: str) -> str:
    db_path = os.getenv("DB_PATH", "master_database.sqlite")
    from src.db_adapter import get_db_connection
    import secrets

    now = datetime.utcnow()
    tok = f"stars_adm_{role.lower()}_{secrets.token_hex(6)}"
    with get_db_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM admin_users WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            aid = row[0] if not hasattr(row, "keys") else row["id"]
            c.execute("UPDATE admin_users SET role = ?, is_active = 1 WHERE id = ?", (role, aid))
        else:
            c.execute(
                """
                INSERT INTO admin_users (username, password_hash, telegram_id, role, is_active, created_at)
                VALUES (?, ?, 700099, ?, 1, ?)
                """,
                (username, hash_password("StarsAdmin123!"), role, now.isoformat()),
            )
            aid = c.lastrowid
        c.execute(
            """
            INSERT INTO admin_sessions (session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at)
            VALUES (?, ?, '127.0.0.1', 'pytest', ?, ?, 0, ?)
            """,
            (tok, aid, now.isoformat(), (now + timedelta(hours=2)).isoformat(), now.isoformat()),
        )
        conn.commit()
    return tok


def test_stars_invoice_api_precheckout_idempotent_fulfillment_and_admin_parity():
    client = TestClient(app)
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99331101
    other_uid = 99331102
    db.get_or_create_user(uid, username="stars_buyer")
    db.get_or_create_user(other_uid, username="stars_other")

    with db._get_connection() as conn:
        conn.execute("UPDATE telegram_users SET is_pro = 0, subscription_expires_at = NULL WHERE user_id = ?", (uid,))
        conn.commit()
    invalidate_user_cache(uid)

    headers = {"X-Telegram-Init-Data": generate_dev_init_data(user_id=uid)}
    other_headers = {"X-Telegram-Init-Data": generate_dev_init_data(user_id=other_uid)}

    # Invalid plan rejected cleanly
    bad_plan = client.post("/api/payment/stars/invoice", json={"plan_id": "invalid_999"}, headers=headers)
    assert bad_plan.status_code == 400

    # Create 14-day Stars invoice (mock Telegram Bot API createInvoiceLink)
    with patch(
        "src.payments.stars_service._request_telegram_invoice_link",
        new=AsyncMock(return_value="https://t.me/$mockStarsInvoice14"),
    ) as mock_link:
        res = client.post("/api/payment/stars/invoice", json={"plan_id": "pro_14"}, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["ok"] is True
        assert data["currency"] == "XTR"
        assert data["stars_amount"] == 78
        assert data["invoice_url"] == "https://t.me/$mockStarsInvoice14"
        assert mock_link.await_args.kwargs["stars_amount"] == 78

    order_id = data["order_id"]
    payload = data["payload"]

    # Other user cannot inspect this invoice (403)
    assert client.get(f"/api/payment/stars/{order_id}/status", headers=other_headers).status_code == 403
    assert client.get("/api/payment/stars/XTR-MISSING-000/status", headers=headers).status_code == 404

    st0 = client.get(f"/api/payment/stars/{order_id}/status", headers=headers).json()
    assert st0["status"] == "PENDING" and st0["is_paid"] is False

    # Pre-checkout validation security checks
    ok_bad_curr, _ = validate_stars_pre_checkout(payload, 78, "UZS", uid)
    assert ok_bad_curr is False
    ok_bad_amt, _ = validate_stars_pre_checkout(payload, 1, "XTR", uid)
    assert ok_bad_amt is False
    ok_bad_user, _ = validate_stars_pre_checkout(payload, 78, "XTR", other_uid)
    assert ok_bad_user is False
    ok_valid, err_valid = validate_stars_pre_checkout(payload, 78, "XTR", uid)
    assert ok_valid is True and err_valid is None

    # First fulfillment activates 14 days PRO
    cap1 = fulfill_stars_payment(
        user_id=uid,
        payload=payload,
        currency="XTR",
        total_amount=78,
        telegram_payment_charge_id="tg_charge_xtr_001",
    )
    assert cap1["ok"] is True and cap1["already_processed"] is False
    exp1 = cap1["expires_at"]

    # Replay with exact same charge_id must NOT double-extend
    cap_dup = fulfill_stars_payment(
        user_id=uid,
        payload=payload,
        currency="XTR",
        total_amount=78,
        telegram_payment_charge_id="tg_charge_xtr_001",
    )
    assert cap_dup["ok"] is True and cap_dup["already_processed"] is True
    sub_after_dup = db.get_user_subscription(uid)
    assert sub_after_dup["is_pro"] is True
    assert sub_after_dup["expires_at"][:16] == exp1[:16]

    # Status endpoint now reports PAID
    st1 = client.get(f"/api/payment/stars/{order_id}/status", headers=headers).json()
    assert st1["status"] == "PAID" and st1["is_paid"] is True

    # Purchasing pro_30 on top extends additively (+30 days -> ~44 days total)
    order30 = asyncio.run(create_stars_invoice_order(uid, "pro_30", create_link=False))
    cap30 = fulfill_stars_payment(
        user_id=uid,
        payload=order30["payload"],
        currency="XTR",
        total_amount=order30["stars_amount"],
        telegram_payment_charge_id="tg_charge_xtr_002",
    )
    assert cap30["ok"] is True and cap30["stars_amount"] == 139
    sub_extended = db.get_user_subscription(uid)
    assert sub_extended["days_left"] >= 42

    # Admin KPI, /stars list & Reconciliation report (HUMO balance remains unbroken)
    fin_tok = _ensure_admin_token("stars_fin_adm", "FINANCE")
    mod_tok = _ensure_admin_token("stars_mod_adm", "MODERATOR")
    assert client.get("/api/admin/payments/stars", headers={"X-Admin-Session": mod_tok}).status_code == 403

    stars_list = client.get("/api/admin/payments/stars?status=PAID", headers={"X-Admin-Session": fin_tok})
    assert stars_list.status_code == 200
    assert any(o["order_id"] == order_id for o in stars_list.json()["orders"])

    rec = client.get("/api/admin/payments/reconciliation", headers={"X-Admin-Session": fin_tok}).json()
    assert rec["is_balanced"] is True and rec["discrepancy_count"] == 0
    assert rec["stars_summary"]["paid_stars_orders"] >= 2
    assert rec["stars_summary"]["total_stars_revenue"] >= 217

    kpi = client.get("/api/admin/dashboard/kpi", headers={"X-Admin-Session": fin_tok}).json()["kpis"]
    assert kpi["stars_payments_count"] >= 2
    assert kpi["stars_revenue_xtr"] >= 217


def test_bot_stars_handlers_and_frontend_parity():
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99331109
    db.get_or_create_user(uid, username="stars_bot_user")

    # 1. /pro command outputs Stars pricing + buy_stars inline buttons
    msg = MagicMock()
    msg.from_user = SimpleNamespace(id=uid, username="stars_bot_user", first_name="Bot", last_name="User")
    msg.answer = AsyncMock()
    asyncio.run(cmd_subscription(msg, db))
    sent_kwargs = msg.answer.await_args.kwargs
    assert "Stars" in sent_kwargs["text"]
    cb_datas = [btn.callback_data for row in sent_kwargs["reply_markup"].inline_keyboard for btn in row if btn.callback_data]
    assert any(d.startswith("buy_stars:") for d in cb_datas)

    # 2. Inline callback buy_stars:pro_14 calls bot.send_invoice with currency="XTR" & provider_token=""
    bot = MagicMock()
    bot.send_invoice = AsyncMock()
    cb = MagicMock()
    cb.data = "buy_stars:pro_14"
    cb.from_user = SimpleNamespace(id=uid, username="stars_bot_user", first_name="Bot", last_name="User")
    cb.message = SimpleNamespace(chat=SimpleNamespace(id=uid))
    cb.answer = AsyncMock()
    asyncio.run(cb_buy_with_telegram_stars(cb, bot, db))
    inv_kw = bot.send_invoice.await_args.kwargs
    assert inv_kw["currency"] == "XTR"
    assert inv_kw["provider_token"] == ""
    assert inv_kw["prices"][0].amount == 78
    created_payload = inv_kw["payload"]

    # 3. PreCheckoutQuery answers ok=True for exact payload/amount, ok=False for tampered amount
    pre_ok = MagicMock()
    pre_ok.invoice_payload = created_payload
    pre_ok.total_amount = 78
    pre_ok.currency = "XTR"
    pre_ok.from_user = SimpleNamespace(id=uid)
    pre_ok.answer = AsyncMock()
    asyncio.run(handle_stars_pre_checkout(pre_ok))
    assert pre_ok.answer.await_args.kwargs["ok"] is True

    pre_tamper = MagicMock()
    pre_tamper.invoice_payload = created_payload
    pre_tamper.total_amount = 5
    pre_tamper.currency = "XTR"
    pre_tamper.from_user = SimpleNamespace(id=uid)
    pre_tamper.answer = AsyncMock()
    asyncio.run(handle_stars_pre_checkout(pre_tamper))
    assert pre_tamper.answer.await_args.kwargs["ok"] is False

    # 4. Successful payment bot handler unlocks PRO and replies in Telegram chat
    pay_msg = MagicMock()
    pay_msg.from_user = SimpleNamespace(id=uid)
    pay_msg.successful_payment = SimpleNamespace(
        invoice_payload=created_payload,
        currency="XTR",
        total_amount=78,
        telegram_payment_charge_id="tg_bot_handler_charge_1",
        provider_payment_charge_id="",
    )
    pay_msg.answer = AsyncMock()
    asyncio.run(handle_stars_successful_payment(pay_msg, db))
    assert db.get_user_subscription(uid)["is_pro"] is True
    assert pay_msg.answer.await_count == 1

    # 5. Frontend profile.js + i18n bundles contain XTR wiring
    prof_js = (ROOT_DIR / "static" / "js" / "views" / "profile.js").read_text(encoding="utf-8")
    assert "/api/payment/stars/invoice" in prof_js
    assert "openInvoice" in prof_js
    for lang in ("uz_latn", "uz_cyrl", "ru"):
        bundle = json.loads((ROOT_DIR / "static" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert "sub_btn_stars" in bundle and "sub_stars_cancelled" in bundle
