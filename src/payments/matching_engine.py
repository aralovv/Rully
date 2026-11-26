"""
Automated Payment Reconciliation & Matching Engine.
Idempotently reconciles incoming Humocardbot notifications with active payment orders.
Implements:
- Strict exact amount matching (Base + Suffix)
- Receiving card verification
- Idempotency and replay protection
- Atomic multi-table state transition via execute_batch() (SQLite + Turso safe)
- Non-blocking asyncio offloading for event loop safety
- Late-payment review queue routing
- Unmatched payment audit logging
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.db_adapter import execute_batch, get_db_connection
from src.payments.order_manager import expire_stale_orders
from src.security.telegram_notifier import (
    send_late_payment_alert_to_admin,
    send_payment_alert_to_admin,
    send_unmatched_payment_alert,
    send_user_payment_success_notification,
)

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def _get_connection():
    return get_db_connection(DB_PATH)


def _inspect_unmatched_candidates(cursor: Any, amount_uzs: int, card_suffix: str) -> Dict[str, Any]:
    """
    Finds near-match pending/expired order candidates to speed up admin resolution
    when a student sent a slightly wrong amount or used a different card.
    """
    # 1. Exact amount on a different card suffix among pending orders
    cursor.execute(
        """
        SELECT order_id, user_id, final_amount_uzs, card_suffix, status
        FROM payment_orders
        WHERE final_amount_uzs = ? AND card_suffix != ? AND status = 'PENDING'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (amount_uzs, card_suffix),
    )
    row = cursor.fetchone()
    if row:
        return {
            "reason_code": "CARD_SUFFIX_MISMATCH",
            "candidate_order_id": row["order_id"],
            "candidate_user_id": row["user_id"],
            "candidate_amount_uzs": row["final_amount_uzs"],
            "candidate_card_suffix": row["card_suffix"],
            "hint": f"Exact amount {amount_uzs} UZS found on pending order for card *{row['card_suffix']}",
        }

    # 2. Same card suffix with close amount (+/- 1000 UZS, e.g. user omitted unique suffix)
    cursor.execute(
        """
        SELECT order_id, user_id, final_amount_uzs, card_suffix, status
        FROM payment_orders
        WHERE card_suffix = ? AND status = 'PENDING'
          AND ABS(final_amount_uzs - ?) <= 1000
        ORDER BY ABS(final_amount_uzs - ?) ASC, created_at DESC
        LIMIT 1
        """,
        (card_suffix, amount_uzs, amount_uzs),
    )
    row = cursor.fetchone()
    if row:
        diff = amount_uzs - int(row["final_amount_uzs"])
        return {
            "reason_code": "NEAR_AMOUNT_PENDING",
            "candidate_order_id": row["order_id"],
            "candidate_user_id": row["user_id"],
            "candidate_amount_uzs": row["final_amount_uzs"],
            "candidate_card_suffix": row["card_suffix"],
            "hint": f"Pending order expects {row['final_amount_uzs']} UZS on *{card_suffix} (delta {diff:+d} UZS)",
        }

    # 3. Expired order with near amount on same card suffix
    cursor.execute(
        """
        SELECT order_id, user_id, final_amount_uzs, card_suffix, status
        FROM payment_orders
        WHERE card_suffix = ? AND status = 'EXPIRED'
          AND ABS(final_amount_uzs - ?) <= 1000
        ORDER BY ABS(final_amount_uzs - ?) ASC, expires_at DESC
        LIMIT 1
        """,
        (card_suffix, amount_uzs, amount_uzs),
    )
    row = cursor.fetchone()
    if row:
        return {
            "reason_code": "EXPIRED_NEAR_MATCH",
            "candidate_order_id": row["order_id"],
            "candidate_user_id": row["user_id"],
            "candidate_amount_uzs": row["final_amount_uzs"],
            "candidate_card_suffix": row["card_suffix"],
            "hint": f"Expired order {row['order_id']} expected {row['final_amount_uzs']} UZS on *{card_suffix}",
        }

    return {
        "reason_code": "NO_CANDIDATE_FOUND",
        "candidate_order_id": None,
        "candidate_user_id": None,
        "candidate_amount_uzs": None,
        "candidate_card_suffix": None,
        "hint": "No pending or near-amount order found matching payment.",
    }


def _compute_extended_expiry_iso(cursor: Any, user_id: int, duration_days: int, now_dt: datetime) -> str:
    cursor.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    base_dt = now_dt
    if u_row and u_row["is_pro"] and u_row["subscription_expires_at"]:
        try:
            curr_exp = datetime.fromisoformat(str(u_row["subscription_expires_at"]).replace("Z", ""))
            if curr_exp > now_dt:
                base_dt = curr_exp
        except Exception:
            pass
    return (base_dt + timedelta(days=duration_days)).isoformat()


def _reconcile_payment_sync(
    parsed: Dict[str, Any],
    source_chat: str,
    message_id: int,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    amount_uzs = parsed.get("amount_uzs", 0)
    card_suffix = parsed.get("card_suffix", "")
    payment_source = parsed.get("payment_source", "UNKNOWN")
    raw_message = parsed.get("raw_message", "")
    trans_time = parsed.get("timestamp_str") or datetime.utcnow().strftime("%d.%m.%Y %H:%M")

    fingerprint_raw = f"{source_chat}:{message_id}:{amount_uzs}:{card_suffix}:{trans_time}"
    event_fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    expire_stale_orders()

    with _get_connection() as conn:
        c = conn.cursor()

        # 1. Duplicate check
        c.execute("SELECT id, status, matched_order_id FROM payment_events WHERE event_fingerprint = ?", (event_fingerprint,))
        existing_event = c.fetchone()
        if existing_event:
            return (
                {
                    "status": "DUPLICATE",
                    "message": "Payment event has already been processed",
                    "event_id": existing_event["id"],
                    "matched_order_id": existing_event["matched_order_id"],
                },
                None,
            )

        # 2. Search for matching ACTIVE (PENDING) order
        c.execute(
            """
            SELECT * FROM payment_orders
            WHERE status = 'PENDING'
              AND final_amount_uzs = ?
              AND card_suffix = ?
              AND expires_at >= ?
            ORDER BY created_at ASC LIMIT 1
            """,
            (amount_uzs, card_suffix, now_str),
        )
        order = c.fetchone()

        # --- SCENARIO 1: EXACT MATCH ON ACTIVE ORDER (100% ATOMIC execute_batch) ---
        if order:
            order_id = order["order_id"]
            user_id = order["user_id"]
            plan_id = order["plan_id"]
            plan_name = order["plan_name"]
            duration_days = order["duration_days"]

            c.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
            user_row = c.fetchone()

            base_dt = now_dt
            if user_row and user_row["is_pro"] and user_row["subscription_expires_at"]:
                try:
                    curr_exp = datetime.fromisoformat(user_row["subscription_expires_at"].replace("Z", ""))
                    if curr_exp > now_dt:
                        base_dt = curr_exp
                except Exception:
                    pass

            new_expires_dt = base_dt + timedelta(days=duration_days)
            new_expires_str = new_expires_dt.isoformat()
            balance_uzs = parsed.get("balance_uzs")

            stmts: List[Any] = [
                (
                    "UPDATE payment_orders SET status = 'PAID', paid_at = ? WHERE order_id = ?",
                    [now_str, order_id],
                ),
                (
                    """
                    INSERT INTO payment_events (
                        event_fingerprint, source_chat, message_id, transaction_type,
                        incoming_amount_uzs, resulting_balance_uzs, card_suffix,
                        payment_source, transaction_timestamp, raw_message,
                        status, matched_order_id, created_at
                    ) VALUES (?, ?, ?, 'INCOMING', ?, ?, ?, ?, ?, ?, 'MATCHED', ?, ?)
                    """,
                    [
                        event_fingerprint, source_chat, message_id, amount_uzs,
                        balance_uzs, card_suffix, payment_source,
                        trans_time, raw_message, order_id, now_str,
                    ],
                ),
                (
                    """
                    INSERT INTO payment_transactions (
                        order_id, user_id, event_id, amount_uzs, plan_id,
                        card_suffix, payment_timestamp, created_at
                    ) VALUES (
                        ?, ?, (SELECT id FROM payment_events WHERE event_fingerprint = ?),
                        ?, ?, ?, ?, ?
                    )
                    """,
                    [
                        order_id, user_id, event_fingerprint, amount_uzs, plan_id,
                        card_suffix, trans_time, now_str,
                    ],
                ),
                (
                    """
                    UPDATE telegram_users
                    SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
                    WHERE user_id = ?
                    """,
                    [plan_id, new_expires_str, user_id],
                ),
                (
                    """
                    INSERT INTO user_subscriptions (
                        user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                    """,
                    [user_id, plan_id, plan_name, duration_days, amount_uzs, now_str, new_expires_str],
                ),
                (
                    """
                    INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
                    VALUES (?, 'PAYMENT_VERIFIED', ?, ?)
                    """,
                    [user_id, json.dumps({"order_id": order_id, "amount": amount_uzs, "plan": plan_id}), now_str],
                ),
                (
                    """
                    INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                    VALUES (0, 'PAYMENT_AUTO_MATCHED', ?, ?)
                    """,
                    [f"Order: {order_id}, User: {user_id}, Amount: {amount_uzs} UZS, Plan: {plan_id}", now_str],
                ),
            ]
            execute_batch(conn, stmts)

            try:
                from src.api.deps import invalidate_user_cache
                invalidate_user_cache(user_id)
            except Exception:
                pass

            return (
                {
                    "status": "MATCHED",
                    "order_id": order_id,
                    "user_id": user_id,
                    "amount_uzs": amount_uzs,
                    "plan_id": plan_id,
                    "subscription_expires_at": new_expires_str,
                },
                {
                    "kind": "MATCHED",
                    "order_id": order_id,
                    "user_id": user_id,
                    "amount_uzs": amount_uzs,
                    "plan_name": plan_name,
                    "duration_days": duration_days,
                    "card_suffix": card_suffix,
                    "expires_at": new_expires_str,
                },
            )

        # --- SCENARIO 2: LATE PAYMENT (Matches recently EXPIRED order atomically) ---
        c.execute(
            """
            SELECT * FROM payment_orders
            WHERE status = 'EXPIRED'
              AND final_amount_uzs = ?
              AND card_suffix = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (amount_uzs, card_suffix),
        )
        expired_order = c.fetchone()

        if expired_order:
            exp_order_id = expired_order["order_id"]
            exp_user_id = expired_order["user_id"]
            balance_uzs = parsed.get("balance_uzs")

            late_stmts: List[Any] = [
                (
                    "UPDATE payment_orders SET status = 'PAYMENT_REVIEW_REQUIRED' WHERE order_id = ?",
                    [exp_order_id],
                ),
                (
                    """
                    INSERT INTO payment_events (
                        event_fingerprint, source_chat, message_id, transaction_type,
                        incoming_amount_uzs, resulting_balance_uzs, card_suffix,
                        payment_source, transaction_timestamp, raw_message,
                        status, matched_order_id, created_at
                    ) VALUES (?, ?, ?, 'INCOMING', ?, ?, ?, ?, ?, ?, 'LATE_REVIEW', ?, ?)
                    """,
                    [
                        event_fingerprint, source_chat, message_id, amount_uzs,
                        balance_uzs, card_suffix, payment_source,
                        trans_time, raw_message, exp_order_id, now_str,
                    ],
                ),
                (
                    """
                    INSERT INTO payment_review_cases (
                        order_id, event_id, user_id, amount_uzs, reason, status, created_at
                    ) VALUES (
                        ?, (SELECT id FROM payment_events WHERE event_fingerprint = ?),
                        ?, ?, 'LATE_PAYMENT', 'PENDING', ?
                    )
                    """,
                    [exp_order_id, event_fingerprint, exp_user_id, amount_uzs, now_str],
                ),
                (
                    """
                    INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                    VALUES (0, 'LATE_PAYMENT_DETECTED', ?, ?)
                    """,
                    [f"Order: {exp_order_id}, User: {exp_user_id}, Amount: {amount_uzs} UZS", now_str],
                ),
            ]
            execute_batch(conn, late_stmts)

            return (
                {
                    "status": "LATE_REVIEW",
                    "message": "Payment arrived after order expiration. Placed in Review Queue.",
                    "order_id": exp_order_id,
                    "user_id": exp_user_id,
                    "amount_uzs": amount_uzs,
                },
                {
                    "kind": "LATE_REVIEW",
                    "order_id": exp_order_id,
                    "user_id": exp_user_id,
                    "amount_uzs": amount_uzs,
                    "card_suffix": card_suffix,
                },
            )

        # --- SCENARIO 3: UNMATCHED PAYMENT (Atomic execute_batch) ---
        diag = _inspect_unmatched_candidates(c, amount_uzs, card_suffix)
        diag_details = (
            f"Amount: {amount_uzs} UZS, Card: {card_suffix}, Source: {payment_source}, "
            f"Reason: {diag['reason_code']}, Candidate: {diag.get('candidate_order_id') or 'none'}"
        )
        unmatched_stmts: List[Any] = [
            (
                """
                INSERT INTO payment_events (
                    event_fingerprint, source_chat, message_id, transaction_type,
                    incoming_amount_uzs, resulting_balance_uzs, card_suffix,
                    payment_source, transaction_timestamp, raw_message,
                    status, matched_order_id, created_at
                ) VALUES (?, ?, ?, 'INCOMING', ?, ?, ?, ?, ?, ?, 'UNMATCHED', NULL, ?)
                """,
                [
                    event_fingerprint, source_chat, message_id, amount_uzs,
                    parsed.get("balance_uzs"), card_suffix, payment_source,
                    trans_time, raw_message, now_str,
                ],
            ),
            (
                """
                INSERT INTO unmatched_payments (
                    event_id, amount_uzs, card_suffix, payment_source, transaction_timestamp, status, created_at
                ) VALUES (
                    (SELECT id FROM payment_events WHERE event_fingerprint = ?),
                    ?, ?, ?, ?, 'UNRESOLVED', ?
                )
                """,
                [event_fingerprint, amount_uzs, card_suffix, payment_source, trans_time, now_str],
            ),
            (
                """
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (0, 'UNMATCHED_PAYMENT_LOGGED', ?, ?)
                """,
                [diag_details, now_str],
            ),
        ]
        execute_batch(conn, unmatched_stmts)

        return (
            {
                "status": "UNMATCHED",
                "message": "No active or expired order found matching exact amount and card.",
                "amount_uzs": amount_uzs,
                "card_suffix": card_suffix,
                "diagnostic": diag,
            },
            {
                "kind": "UNMATCHED",
                "amount_uzs": amount_uzs,
                "card_suffix": card_suffix,
                "payment_source": payment_source,
                "diagnostic_hint": diag["hint"],
                "candidate_order_id": diag.get("candidate_order_id"),
            },
        )


def link_unmatched_to_order_sync(
    unmatched_id: int,
    order_id: str,
    admin_id: int,
    admin_username: str,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Atomically links an UNRESOLVED unmatched payment to a target pending/expired order,
    activates or extends PRO, writes payment_transactions, and records admin audit log.
    """
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM unmatched_payments WHERE id = ? AND status = 'UNRESOLVED'",
            (unmatched_id,),
        )
        unmatched = c.fetchone()
        if not unmatched:
            raise ValueError("Unresolved unmatched payment not found")

        c.execute(
            """
            SELECT * FROM payment_orders
            WHERE order_id = ? AND status IN ('PENDING', 'EXPIRED')
            """,
            (order_id,),
        )
        order = c.fetchone()
        if not order:
            raise ValueError("Target pending/expired order not found")

        user_id = int(order["user_id"])
        plan_id = order["plan_id"]
        plan_name = order["plan_name"]
        duration_days = int(order["duration_days"])
        amount_uzs = int(unmatched["amount_uzs"])
        card_suffix = unmatched["card_suffix"]
        event_id = unmatched["event_id"]

        new_expires_str = _compute_extended_expiry_iso(c, user_id, duration_days, now_dt)
        audit_note = notes.strip() or f"Linked unmatched #{unmatched_id} to order {order_id}"

        execute_batch(
            conn,
            [
                (
                    """
                    UPDATE unmatched_payments
                    SET status = 'RESOLVED_LINKED', resolution_notes = ?, resolved_by_admin = ?, resolved_at = ?
                    WHERE id = ? AND status = 'UNRESOLVED'
                    """,
                    [audit_note, admin_username, now_str, unmatched_id],
                ),
                (
                    "UPDATE payment_orders SET status = 'PAID', paid_at = ? WHERE order_id = ?",
                    [now_str, order_id],
                ),
                (
                    "UPDATE payment_events SET status = 'MATCHED', matched_order_id = ? WHERE id = ?",
                    [order_id, event_id],
                ),
                (
                    """
                    INSERT INTO payment_transactions (
                        order_id, user_id, event_id, amount_uzs, plan_id, card_suffix, payment_timestamp, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [order_id, user_id, event_id, amount_uzs, plan_id, card_suffix, now_str, now_str],
                ),
                (
                    """
                    UPDATE telegram_users
                    SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
                    WHERE user_id = ?
                    """,
                    [plan_id, new_expires_str, user_id],
                ),
                (
                    """
                    INSERT INTO user_subscriptions (
                        user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                    """,
                    [user_id, plan_id, plan_name, duration_days, amount_uzs, now_str, new_expires_str],
                ),
                (
                    """
                    INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                    VALUES (?, 'UNMATCHED_PAYMENT_LINKED', ?, ?)
                    """,
                    [admin_id, f"Unmatched: {unmatched_id}, Order: {order_id}, User: {user_id}, Notes: {audit_note}", now_str],
                ),
            ],
        )

    try:
        from src.api.deps import invalidate_user_cache
        invalidate_user_cache(user_id)
    except Exception:
        pass

    return {
        "ok": True,
        "unmatched_id": unmatched_id,
        "order_id": order_id,
        "user_id": user_id,
        "plan_name": plan_name,
        "duration_days": duration_days,
        "amount_uzs": amount_uzs,
        "expires_at": new_expires_str,
    }


def get_payment_reconciliation_health_sync() -> Dict[str, Any]:
    """Returns compact financial reconciliation and queue observability telemetry."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                COUNT(*) AS total_events,
                SUM(CASE WHEN status = 'MATCHED' THEN 1 ELSE 0 END) AS matched_events,
                SUM(CASE WHEN status = 'LATE_REVIEW' THEN 1 ELSE 0 END) AS late_review_events,
                SUM(CASE WHEN status = 'UNMATCHED' THEN 1 ELSE 0 END) AS unmatched_events,
                MAX(created_at) AS last_event_at
            FROM payment_events
            """
        )
        ev = dict(c.fetchone() or {})
        c.execute("SELECT COUNT(*) FROM unmatched_payments WHERE status = 'UNRESOLVED'")
        unresolved_unmatched = int(c.fetchone()[0] or 0)
        c.execute("SELECT COUNT(*) FROM payment_review_cases WHERE status = 'PENDING'")
        pending_reviews = int(c.fetchone()[0] or 0)
        c.execute("SELECT COUNT(*) FROM payment_orders WHERE status = 'PENDING'")
        pending_orders = int(c.fetchone()[0] or 0)
        c.execute("SELECT COUNT(*) FROM payment_transactions")
        ledger_tx = int(c.fetchone()[0] or 0)

    matched_ev = int(ev.get("matched_events") or 0)
    discrepancy = abs(matched_ev - ledger_tx)
    return {
        "total_events": int(ev.get("total_events") or 0),
        "matched_events": matched_ev,
        "late_review_events": int(ev.get("late_review_events") or 0),
        "unmatched_events": int(ev.get("unmatched_events") or 0),
        "unresolved_unmatched": unresolved_unmatched,
        "pending_reviews": pending_reviews,
        "pending_orders": pending_orders,
        "ledger_transactions": ledger_tx,
        "discrepancy_count": discrepancy,
        "is_balanced": discrepancy == 0,
        "last_event_at": ev.get("last_event_at"),
    }


async def process_incoming_payment_event(
    parsed: Dict[str, Any],
    source_chat: str = "Humocardbot",
    message_id: int = 0,
) -> Dict[str, Any]:
    """
    Main payment ingestion entrypoint.
    Executes transaction-safe matching via threadpool + execute_batch().
    """
    if not parsed or not parsed.get("is_incoming"):
        return {"status": "SKIPPED", "reason": "Not an incoming transaction"}

    amount_uzs = parsed.get("amount_uzs", 0)
    card_suffix = parsed.get("card_suffix", "")
    if amount_uzs <= 0 or not card_suffix:
        return {"status": "MALFORMED", "reason": "Missing valid amount or card suffix"}

    result, notify = await asyncio.to_thread(_reconcile_payment_sync, parsed, source_chat, message_id)

    if notify:
        try:
            kind = notify["kind"]
            if kind == "MATCHED":
                await send_user_payment_success_notification(
                    notify["user_id"],
                    notify["plan_name"],
                    notify["expires_at"],
                    duration_days=notify["duration_days"],
                )
                await send_payment_alert_to_admin(
                    notify["order_id"],
                    notify["amount_uzs"],
                    notify["user_id"],
                    notify["plan_name"],
                    notify["card_suffix"],
                )
            elif kind == "LATE_REVIEW":
                await send_late_payment_alert_to_admin(
                    notify["order_id"],
                    notify["amount_uzs"],
                    notify["user_id"],
                    notify["card_suffix"],
                )
            elif kind == "UNMATCHED":
                await send_unmatched_payment_alert(
                    notify["amount_uzs"],
                    notify["card_suffix"],
                    notify["payment_source"],
                    diagnostic_hint=notify.get("diagnostic_hint"),
                    candidate_order_id=notify.get("candidate_order_id"),
                )
        except Exception as e:
            logger.error(f"Error sending payment notification ({notify.get('kind')}): {e}")

    return result
