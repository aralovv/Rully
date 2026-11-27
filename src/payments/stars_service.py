"""
Native Telegram Stars (XTR) Payment Service for RULLY PRO.

Handles:
- Dynamic Stars invoice link creation via Telegram Bot API (`currency="XTR"`, `provider_token=""`)
- Strict `pre_checkout_query` verification (payload ownership, exact Stars amount, pending status)
- Idempotent, atomic PRO activation across SQLite & Turso (`execute_batch`)
- Safe polling status endpoint for Mini App `WebApp.openInvoice` & web fallback
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from src.db_adapter import execute_batch, get_db_connection, is_turso_enabled
from src.payments.order_manager import compute_stars_price, get_subscription_plan

logger = logging.getLogger(__name__)

STARS_ORDER_LIFETIME_MINUTES = 30
_STARS_SCHEMA_READY: Set[str] = set()
_STARS_SCHEMA_LOCK = Lock()


def _get_connection():
    db_path = os.getenv("DB_PATH", "master_database.sqlite")
    return get_db_connection(db_path)


def _ensure_stars_schema(conn: Any) -> None:
    db_path = os.getenv("DB_PATH", "master_database.sqlite")
    cache_key = "__turso__" if is_turso_enabled() else os.path.abspath(db_path)
    with _STARS_SCHEMA_LOCK:
        if cache_key in _STARS_SCHEMA_READY:
            return
    execute_batch(
        conn,
        [
            """
            CREATE TABLE IF NOT EXISTS payment_stars_orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                stars_amount INTEGER NOT NULL,
                uzs_equivalent INTEGER NOT NULL,
                payload TEXT UNIQUE NOT NULL,
                invoice_url TEXT,
                telegram_payment_charge_id TEXT UNIQUE,
                provider_payment_charge_id TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
                FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
            )
            """.strip(),
            "CREATE INDEX IF NOT EXISTS idx_stars_orders_user ON payment_stars_orders(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_stars_orders_status ON payment_stars_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_stars_orders_payload ON payment_stars_orders(payload)",
            """
            CREATE TABLE IF NOT EXISTS payment_stars_charges (
                charge_id TEXT PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PAID',
                created_at TEXT NOT NULL,
                refunded_at TEXT
            )
            """.strip(),
        ],
    )
    with _STARS_SCHEMA_LOCK:
        _STARS_SCHEMA_READY.add(cache_key)


def _get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if token:
        return token
    try:
        from src.bot.config import BOT_TOKEN
        return str(BOT_TOKEN or "").strip()
    except Exception:
        return ""


async def _request_telegram_invoice_link(
    bot_token: str,
    title: str,
    description: str,
    payload: str,
    stars_amount: int,
    label: str,
) -> str:
    """Calls Telegram Bot API `createInvoiceLink` for XTR digital goods."""
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured for Telegram Stars payments.")

    url = f"https://api.telegram.org/bot{bot_token}/createInvoiceLink"
    req_body = {
        "title": title[:32],
        "description": description[:255],
        "payload": payload,
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": label[:32], "amount": int(stars_amount)}],
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(url, json=req_body)

    if resp.status_code != 200:
        raise RuntimeError(f"Telegram createInvoiceLink HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if not data.get("ok") or not data.get("result"):
        raise RuntimeError(f"Telegram createInvoiceLink rejected: {data.get('description') or 'unknown error'}")
    return str(data["result"])


async def create_stars_invoice_order(
    user_id: int,
    plan_id: str,
    create_link: bool = True,
) -> Dict[str, Any]:
    """
    Creates a pending Telegram Stars (`XTR`) order and optionally requests an `invoice_url`
    via `createInvoiceLink` for Telegram Mini App `WebApp.openInvoice(...)`.
    """
    clean_plan_id = str(plan_id or "").strip()
    plan = get_subscription_plan(clean_plan_id)
    if not plan:
        raise ValueError(f"Tanlangan tarif ({clean_plan_id}) mavjud emas yoki faol emas.")

    stars_amount = compute_stars_price(plan)
    uzs_equivalent = int(plan.get("base_price_uzs") or 0)
    duration_days = int(plan.get("duration_days") or 14)
    plan_name = str(plan.get("name") or clean_plan_id)

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    expires_dt = now_dt + timedelta(minutes=STARS_ORDER_LIFETIME_MINUTES)
    expires_str = expires_dt.isoformat()

    order_id = f"XTR-{now_dt.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
    payload = f"rully_xtr:{order_id}:{int(user_id)}:{clean_plan_id}"

    with _get_connection() as conn:
        _ensure_stars_schema(conn)
        execute_batch(
            conn,
            [
                (
                    """
                    INSERT INTO payment_stars_orders (
                        order_id, user_id, plan_id, plan_name, duration_days,
                        stars_amount, uzs_equivalent, payload, invoice_url, status,
                        created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'PENDING', ?, ?)
                    """,
                    [
                        order_id,
                        int(user_id),
                        clean_plan_id,
                        plan_name,
                        duration_days,
                        stars_amount,
                        uzs_equivalent,
                        payload,
                        now_str,
                        expires_str,
                    ],
                ),
                (
                    """
                    INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
                    VALUES (?, 'STARS_INVOICE_CREATED', ?, ?)
                    """,
                    [
                        int(user_id),
                        json.dumps({"order_id": order_id, "plan_id": clean_plan_id, "stars_amount": stars_amount}),
                        now_str,
                    ],
                ),
            ],
        )

    invoice_url: Optional[str] = None
    if create_link:
        title = f"RULLY PRO — {plan_name}"
        description = (
            f"{duration_days} kunlik to‘liq PRO kirish: "
            "Cheksiz DYHXX imtihonlar, AI Ustoz 2.0, Avtodrom 2D va Shpargalka."
        )
        try:
            invoice_url = await _request_telegram_invoice_link(
                bot_token=_get_bot_token(),
                title=title,
                description=description,
                payload=payload,
                stars_amount=stars_amount,
                label=plan_name,
            )
            with _get_connection() as conn:
                conn.execute(
                    "UPDATE payment_stars_orders SET invoice_url = ? WHERE order_id = ?",
                    (invoice_url, order_id),
                )
                conn.commit()
        except Exception:
            with _get_connection() as conn:
                conn.execute(
                    "UPDATE payment_stars_orders SET status = 'FAILED' WHERE order_id = ?",
                    (order_id,),
                )
                conn.commit()
            raise

    return {
        "ok": True,
        "order_id": order_id,
        "plan_id": clean_plan_id,
        "plan_name": plan_name,
        "duration_days": duration_days,
        "stars_amount": stars_amount,
        "uzs_equivalent": uzs_equivalent,
        "currency": "XTR",
        "payload": payload,
        "invoice_url": invoice_url,
        "expires_at": expires_str,
        "remaining_seconds": STARS_ORDER_LIFETIME_MINUTES * 60,
    }


def get_stars_order_status(order_id: str, user_id: int) -> Tuple[int, Dict[str, Any]]:
    """Fetches a Telegram Stars order status after validating ownership."""
    with _get_connection() as conn:
        _ensure_stars_schema(conn)
        c = conn.cursor()
        c.execute("SELECT * FROM payment_stars_orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        if not row:
            return 404, {"detail": "Stars order not found"}
        order = dict(row)
        if int(order["user_id"]) != int(user_id):
            return 403, {"detail": "Forbidden: Order belongs to another user"}

        now_dt = datetime.utcnow()
        remaining = 0
        if order.get("expires_at"):
            try:
                exp_dt = datetime.fromisoformat(str(order["expires_at"]).replace("Z", ""))
                if order["status"] == "PENDING" and now_dt >= exp_dt:
                    c.execute(
                        "UPDATE payment_stars_orders SET status = 'EXPIRED' WHERE order_id = ?",
                        (order_id,),
                    )
                    conn.commit()
                    order["status"] = "EXPIRED"
                remaining = max(0, int((exp_dt - now_dt).total_seconds()))
            except Exception:
                remaining = 0

    return 200, {
        "ok": True,
        "order_id": order["order_id"],
        "plan_id": order["plan_id"],
        "plan_name": order["plan_name"],
        "stars_amount": int(order["stars_amount"]),
        "currency": "XTR",
        "status": order["status"],
        "is_paid": order["status"] == "PAID",
        "is_expired": order["status"] == "EXPIRED",
        "remaining_seconds": remaining,
        "paid_at": order.get("paid_at"),
    }


def validate_stars_pre_checkout(
    payload: str,
    total_amount: int,
    currency: str,
    user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Validates Telegram `PreCheckoutQuery` strictly before Stars are deducted.
    Returns `(True, None)` when valid, or `(False, user_facing_error)` otherwise.
    """
    if str(currency or "").upper() != "XTR":
        return False, "Faqat Telegram Stars (XTR) valyutasi qo‘llab-quvvatlanadi."
    if not payload:
        return False, "To‘lov identifikatori topilmadi."

    with _get_connection() as conn:
        _ensure_stars_schema(conn)
        c = conn.cursor()
        c.execute("SELECT * FROM payment_stars_orders WHERE payload = ?", (payload,))
        row = c.fetchone()
        if not row:
            return False, "Buyurtma topilmadi yoki muddati tugagan."
        order = dict(row)

    if int(order["user_id"]) != int(user_id):
        return False, "Buyurtma boshqa foydalanuvchiga tegishli."
    if int(order["stars_amount"]) != int(total_amount):
        return False, "To‘lov summasi tarif narxi bilan mos kelmadi."
    if order["status"] == "PAID":
        return False, "Bu buyurtma allaqachon to‘langan."
    if order["status"] not in ("PENDING",):
        return False, "Buyurtma holati yaroqsiz. Iltimos, qaytadan urinib ko‘ring."

    exp_raw = order.get("expires_at")
    if exp_raw:
        try:
            exp_dt = datetime.fromisoformat(str(exp_raw).replace("Z", ""))
            if datetime.utcnow() >= exp_dt:
                with _get_connection() as conn:
                    conn.execute(
                        "UPDATE payment_stars_orders SET status = 'EXPIRED' WHERE order_id = ? AND status = 'PENDING'",
                        (order["order_id"],),
                    )
                    conn.commit()
                return False, "Buyurtma muddati tugagan. Iltimos, yangi to‘lov yarating."
        except Exception:
            pass

    if not get_subscription_plan(order["plan_id"]):
        return False, "Tanlangan tarif hozirda faol emas."
    return True, None


def fulfill_stars_payment(
    user_id: int,
    payload: str,
    currency: str,
    total_amount: int,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Idempotently fulfills a verified `successful_payment` (`XTR`) update:
    marks the order PAID and extends user PRO subscription atomically.
    """
    if str(currency or "").upper() != "XTR":
        return {"ok": False, "reason": "INVALID_CURRENCY"}
    charge_id = str(telegram_payment_charge_id or "").strip()
    if not charge_id:
        return {"ok": False, "reason": "MISSING_CHARGE_ID"}

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        _ensure_stars_schema(conn)
        c = conn.cursor()

        # 1. Charge-ID replay idempotency guard
        c.execute(
            "SELECT * FROM payment_stars_orders WHERE telegram_payment_charge_id = ?",
            (charge_id,),
        )
        dup_row = c.fetchone()
        if dup_row:
            dup = dict(dup_row)
            return {
                "ok": True,
                "already_processed": True,
                "order_id": dup["order_id"],
                "user_id": int(dup["user_id"]),
                "plan_id": dup["plan_id"],
                "plan_name": dup["plan_name"],
                "stars_amount": int(dup["stars_amount"]),
                "duration_days": int(dup["duration_days"]),
            }

        # 2. Load order by unique payload
        c.execute("SELECT * FROM payment_stars_orders WHERE payload = ?", (payload,))
        order_row = c.fetchone()
        if not order_row:
            return {"ok": False, "reason": "ORDER_NOT_FOUND"}
        order = dict(order_row)

        if int(order["user_id"]) != int(user_id):
            return {"ok": False, "reason": "USER_MISMATCH"}
        if int(order["stars_amount"]) != int(total_amount):
            return {"ok": False, "reason": "AMOUNT_MISMATCH"}
        if order["status"] == "PAID":
            return {
                "ok": True,
                "already_processed": True,
                "order_id": order["order_id"],
                "user_id": int(user_id),
                "plan_id": order["plan_id"],
                "plan_name": order["plan_name"],
                "stars_amount": int(order["stars_amount"]),
                "duration_days": int(order["duration_days"]),
            }

        order_id = order["order_id"]
        plan_id = order["plan_id"]
        plan_name = order["plan_name"]
        duration_days = int(order["duration_days"])
        stars_amount = int(order["stars_amount"])

        # 3. Compute additive PRO expiry timestamp
        c.execute(
            "SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?",
            (int(user_id),),
        )
        u_row = c.fetchone()
        base_dt = now_dt
        if u_row and u_row["is_pro"] and u_row["subscription_expires_at"]:
            try:
                cur_exp = datetime.fromisoformat(str(u_row["subscription_expires_at"]).replace("Z", ""))
                if cur_exp > now_dt:
                    base_dt = cur_exp
            except Exception:
                pass

        new_expires_str = (base_dt + timedelta(days=duration_days)).isoformat()
        sub_label = f"{plan_name} ({stars_amount} XTR)"

        stmts: List[Any] = [
            (
                """
                INSERT INTO payment_stars_charges (charge_id, order_id, user_id, status, created_at)
                VALUES (?, ?, ?, 'PAID', ?)
                """,
                [charge_id, order_id, int(user_id), now_str],
            ),
            (
                """
                UPDATE payment_stars_orders
                SET status = 'PAID',
                    telegram_payment_charge_id = ?,
                    provider_payment_charge_id = ?,
                    paid_at = ?
                WHERE order_id = ? AND status != 'PAID'
                """,
                [charge_id, provider_payment_charge_id or "", now_str, order_id],
            ),
            (
                """
                UPDATE telegram_users
                SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
                WHERE user_id = ?
                """,
                [plan_id, new_expires_str, int(user_id)],
            ),
            (
                """
                INSERT INTO user_subscriptions (
                    user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, 0, 'ACTIVE', ?, ?)
                """,
                [int(user_id), plan_id, sub_label, duration_days, now_str, new_expires_str],
            ),
            (
                """
                INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
                VALUES (?, 'STARS_PAYMENT_VERIFIED', ?, ?)
                """,
                [
                    int(user_id),
                    json.dumps(
                        {
                            "order_id": order_id,
                            "plan_id": plan_id,
                            "stars_amount": stars_amount,
                            "charge_id": charge_id,
                        }
                    ),
                    now_str,
                ],
            ),
            (
                """
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (0, 'STARS_PAYMENT_COMPLETED', ?, ?)
                """,
                [
                    f"Order: {order_id}, User: {user_id}, Stars: {stars_amount} XTR, Plan: {plan_id}, Charge: {charge_id}",
                    now_str,
                ],
            ),
        ]
        try:
            execute_batch(conn, stmts)
        except Exception as exc:
            err_upper = str(exc).upper()
            if isinstance(exc, sqlite3.IntegrityError) or "UNIQUE" in err_upper or "CONSTRAINT" in err_upper:
                c.execute(
                    "SELECT * FROM payment_stars_orders WHERE telegram_payment_charge_id = ? OR order_id = ?",
                    (charge_id, order_id),
                )
                race_row = c.fetchone()
                if race_row:
                    race = dict(race_row)
                    return {
                        "ok": True,
                        "already_processed": True,
                        "order_id": race["order_id"],
                        "user_id": int(race["user_id"]),
                        "plan_id": race["plan_id"],
                        "plan_name": race["plan_name"],
                        "stars_amount": int(race["stars_amount"]),
                        "duration_days": int(race["duration_days"]),
                    }
            raise

    try:
        from src.api.deps import invalidate_user_cache
        invalidate_user_cache(int(user_id))
    except Exception:
        pass

    return {
        "ok": True,
        "already_processed": False,
        "order_id": order_id,
        "user_id": int(user_id),
        "plan_id": plan_id,
        "plan_name": plan_name,
        "stars_amount": stars_amount,
        "duration_days": duration_days,
        "expires_at": new_expires_str,
        "charge_id": charge_id,
    }


def refund_stars_payment(
    user_id: int,
    currency: str,
    total_amount: int,
    telegram_payment_charge_id: str,
    invoice_payload: Optional[str] = None,
    provider_payment_charge_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Idempotently handles Telegram Stars (`XTR`) refund clawbacks (`refunded_payment`):
    marks order & charge REFUNDED and revokes granted PRO duration atomically.
    """
    if str(currency or "").upper() != "XTR":
        return {"ok": False, "reason": "INVALID_CURRENCY"}
    charge_id = str(telegram_payment_charge_id or "").strip()
    if not charge_id:
        return {"ok": False, "reason": "MISSING_CHARGE_ID"}

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        _ensure_stars_schema(conn)
        c = conn.cursor()
        c.execute(
            "SELECT * FROM payment_stars_orders WHERE telegram_payment_charge_id = ? OR (? != '' AND payload = ?)",
            (charge_id, str(invoice_payload or ""), str(invoice_payload or "")),
        )
        row = c.fetchone()
        if not row:
            return {"ok": False, "reason": "ORDER_NOT_FOUND"}
        order = dict(row)

        target_user_id = int(order["user_id"])
        if user_id and int(user_id) != target_user_id:
            return {"ok": False, "reason": "USER_MISMATCH"}

        order_id = order["order_id"]
        prev_status = order["status"]
        if prev_status in ("REFUNDED", "REFUNDING"):
            return {
                "ok": True,
                "already_refunded": True,
                "order_id": order_id,
                "user_id": target_user_id,
                "plan_id": order["plan_id"],
                "plan_name": order["plan_name"],
                "stars_amount": int(order["stars_amount"]),
            }

        # Atomic state-claim lock BEFORE computing duration subtraction (prevents double-deduction on concurrent webhooks)
        c.execute(
            "UPDATE payment_stars_orders SET status = 'REFUNDING' WHERE order_id = ? AND status IN ('PAID', 'PENDING')",
            (order_id,),
        )
        conn.commit()
        if (c.rowcount or 0) != 1:
            return {
                "ok": True,
                "already_refunded": True,
                "order_id": order_id,
                "user_id": target_user_id,
                "plan_id": order["plan_id"],
                "plan_name": order["plan_name"],
                "stars_amount": int(order["stars_amount"]),
            }

        duration_days = int(order["duration_days"])
        stars_amount = int(order["stars_amount"])

        try:
            c.execute(
                "SELECT is_pro, subscription_tier, subscription_expires_at FROM telegram_users WHERE user_id = ?",
                (target_user_id,),
            )
            u_row = c.fetchone()
            new_is_pro = 0
            new_tier = "FREE"
            new_exp_str: Optional[str] = None

            if u_row and u_row["is_pro"] and u_row["subscription_expires_at"]:
                try:
                    cur_exp = datetime.fromisoformat(str(u_row["subscription_expires_at"]).replace("Z", ""))
                    adjusted = cur_exp - timedelta(days=duration_days)
                    if adjusted > now_dt:
                        new_is_pro = 1
                        new_tier = u_row["subscription_tier"] or order["plan_id"]
                        new_exp_str = adjusted.isoformat()
                except Exception:
                    pass

            execute_batch(
                conn,
                [
                    (
                        "UPDATE payment_stars_orders SET status = 'REFUNDED' WHERE order_id = ? AND status = 'REFUNDING'",
                        [order_id],
                    ),
                    (
                        "UPDATE payment_stars_charges SET status = 'REFUNDED', refunded_at = ? WHERE charge_id = ? OR order_id = ?",
                        [now_str, charge_id, order_id],
                    ),
                    (
                        """
                        UPDATE telegram_users
                        SET is_pro = ?, subscription_tier = ?, subscription_expires_at = ?
                        WHERE user_id = ?
                        """,
                        [new_is_pro, new_tier, new_exp_str, target_user_id],
                    ),
                    (
                        """
                        UPDATE user_subscriptions
                        SET status = 'REFUNDED'
                        WHERE id = (
                            SELECT id FROM user_subscriptions
                            WHERE user_id = ? AND plan_id = ? AND status = 'ACTIVE'
                            ORDER BY created_at DESC LIMIT 1
                        )
                        """,
                        [target_user_id, order["plan_id"]],
                    ),
                    (
                        """
                        INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
                        VALUES (?, 'STARS_PAYMENT_REFUNDED', ?, ?)
                        """,
                        [
                            target_user_id,
                            json.dumps(
                                {
                                    "order_id": order_id,
                                    "charge_id": charge_id,
                                    "stars_amount": total_amount or stars_amount,
                                    "revoked_days": duration_days,
                                    "still_pro": bool(new_is_pro),
                                }
                            ),
                            now_str,
                        ],
                    ),
                    (
                        """
                        INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                        VALUES (0, 'STARS_PAYMENT_REFUNDED', ?, ?)
                        """,
                        [
                            f"Order: {order_id}, User: {target_user_id}, Stars: {total_amount or stars_amount} XTR, Charge: {charge_id}",
                            now_str,
                        ],
                    ),
                ],
            )
        except Exception:
            try:
                conn.execute(
                    "UPDATE payment_stars_orders SET status = ? WHERE order_id = ? AND status = 'REFUNDING'",
                    (prev_status, order_id),
                )
                conn.commit()
            except Exception:
                pass
            raise

    try:
        from src.api.deps import invalidate_user_cache
        invalidate_user_cache(target_user_id)
    except Exception:
        pass

    return {
        "ok": True,
        "already_refunded": False,
        "order_id": order_id,
        "user_id": target_user_id,
        "plan_id": order["plan_id"],
        "plan_name": order["plan_name"],
        "stars_amount": total_amount or stars_amount,
        "pro_active": bool(new_is_pro),
        "expires_at": new_exp_str,
    }
