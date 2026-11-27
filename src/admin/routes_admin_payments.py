"""
Admin Payment Reconciliation, Unmatched Payments, and Review Queue Routes.
Supports:
- Verified transaction ledger inspection
- Late payment review queue resolution (manual approval or rejection)
- Unmatched payment audit and linking
- Financial reconciliation discrepancy reporting
"""

import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin, require_admin_role
from src.db_adapter import execute_batch, fetch_batch_dicts, get_db_connection
try:
    from src.mtproto.service import get_mtproto_manager
except ImportError:
    get_mtproto_manager = None
from src.payments.matching_engine import (
    _compute_extended_expiry_iso,
    _match_candidate_from_orders,
    get_payment_reconciliation_health_sync,
    link_unmatched_to_order_sync,
)
from src.security.telegram_notifier import send_user_payment_success_notification, send_late_payment_approved_alert

router = APIRouter(
    prefix="/api/admin/payments",
    tags=["Admin Payments & Reconciliation"],
    dependencies=[Depends(require_admin_role("FINANCE"))],
)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")

def _get_connection():
    return get_db_connection(DB_PATH)


class ResolveReviewRequest(BaseModel):
    notes: Optional[str] = Field("", description="Admin resolution notes")
    note: Optional[str] = Field(None, description="Backward-compatible alias for resolution notes")

    def resolved_notes(self) -> str:
        return (self.notes or self.note or "").strip()


class ResolveUnmatchedRequest(BaseModel):
    status: str = Field("RESOLVED_REFUNDED", description="RESOLVED_LINKED, RESOLVED_REFUNDED, IGNORED")
    notes: str = Field(..., description="Resolution explanation")


class LinkUnmatchedOrderRequest(BaseModel):
    order_id: str = Field(..., description="Target PENDING or EXPIRED order_id to link")
    notes: Optional[str] = Field("", description="Administrative audit explanation")


@router.get("/transactions")
def list_payment_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search by Order ID, User ID, or Plan ID"),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists verified financial transactions ledger."""
    offset = (page - 1) * limit
    conditions = []
    params = []

    if q:
        q_clean = f"%{q.strip()}%"
        conditions.append("(t.order_id LIKE ? OR CAST(t.user_id AS TEXT) LIKE ? OR t.plan_id LIKE ? OR u.username LIKE ?)")
        params.extend([q_clean, q_clean, q_clean, q_clean])

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM payment_transactions t LEFT JOIN telegram_users u ON t.user_id = u.user_id {where_clause}", params)
        total_items = c.fetchone()[0]

        c.execute(f"""
            SELECT t.*, u.username, u.first_name, u.last_name
            FROM payment_transactions t
            LEFT JOIN telegram_users u ON t.user_id = u.user_id
            {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        transactions = [dict(r) for r in c.fetchall()]

    return {
        "ok": True,
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": (total_items + limit - 1) // limit if limit else 1,
        "transactions": transactions
    }


@router.get("/unmatched")
def list_unmatched_payments(
    status: Optional[str] = Query(None, description="UNRESOLVED, RESOLVED_LINKED, RESOLVED_REFUNDED, IGNORED"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists incoming payments from Humocardbot with 1-RT batched candidate near-match hints."""
    offset = (page - 1) * limit
    conditions = []
    params = []

    if status:
        conditions.append("u.status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        batches = fetch_batch_dicts(
            conn,
            [
                (f"SELECT COUNT(*) AS cnt FROM unmatched_payments u {where_clause}", list(params)),
                (
                    f"""
                    SELECT u.*, u.amount_uzs AS incoming_amount_uzs, e.raw_message, e.source_chat
                    FROM unmatched_payments u
                    LEFT JOIN payment_events e ON u.event_id = e.id
                    {where_clause}
                    ORDER BY u.created_at DESC
                    LIMIT ? OFFSET ?
                    """.strip(),
                    list(params) + [limit, offset],
                ),
                (
                    """
                    SELECT order_id, user_id, final_amount_uzs, card_suffix, status, created_at, expires_at
                    FROM payment_orders
                    WHERE status IN ('PENDING', 'EXPIRED')
                    ORDER BY created_at DESC
                    LIMIT 500
                    """.strip(),
                    [],
                ),
            ],
        )

    total_items = int(batches[0][0]["cnt"] or 0) if batches[0] else 0
    cand_orders = batches[2]
    unmatched = []
    for item in batches[1]:
        if item.get("status") == "UNRESOLVED":
            cand = _match_candidate_from_orders(
                cand_orders,
                int(item.get("amount_uzs") or 0),
                str(item.get("card_suffix") or ""),
            )
            item["candidate_order_id"] = cand.get("candidate_order_id")
            item["candidate_hint"] = cand.get("hint")
            item["candidate_reason"] = cand.get("reason_code")
        else:
            item.setdefault("candidate_order_id", None)
            item.setdefault("candidate_hint", None)
        unmatched.append(item)

    return {
        "ok": True,
        "total": total_items,
        "page": page,
        "limit": limit,
        "unmatched": unmatched
    }


@router.post("/unmatched/{unmatched_id}/resolve")
def resolve_unmatched_payment(
    unmatched_id: int,
    req: ResolveUnmatchedRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Resolves an unmatched payment case with administrative audit notes atomically."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE unmatched_payments
            SET status = ?, resolution_notes = ?, resolved_by_admin = ?, resolved_at = ?
            WHERE id = ? AND status = 'UNRESOLVED'
            """,
            (req.status, req.notes, current_admin["username"], now_str, unmatched_id),
        )
        if (c.rowcount or 0) != 1:
            raise HTTPException(status_code=404, detail="Unresolved unmatched payment record not found")

        c.execute(
            """
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'UNMATCHED_PAYMENT_RESOLVED', ?, ?)
            """,
            (current_admin["id"], f"ID: {unmatched_id}, Status: {req.status}, Notes: {req.notes}", now_str),
        )
        conn.commit()

    return {"ok": True, "message": "Holat muvaffaqiyatli hal qilindi."}


@router.post("/unmatched/{unmatched_id}/link-order")
async def link_unmatched_payment_to_order(
    unmatched_id: int,
    req: LinkUnmatchedOrderRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Atomically links an unresolved Humo payment to a pending/expired order,
    writes payment_transactions ledger entry, and activates user PRO subscription.
    """
    admin_name = current_admin["username"]
    try:
        res = await asyncio.to_thread(
            link_unmatched_to_order_sync,
            unmatched_id,
            req.order_id.strip(),
            current_admin["id"],
            admin_name,
            req.notes or "",
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    try:
        await send_user_payment_success_notification(
            res["user_id"],
            res["plan_name"],
            res["expires_at"],
            duration_days=res["duration_days"],
        )
        await send_late_payment_approved_alert(
            res["order_id"],
            res["amount_uzs"],
            res["user_id"],
            res["plan_name"],
            admin_name,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Noma’lum to‘lov buyurtmaga ({res['order_id']}) bog‘landi va PRO faollashtirildi.",
        **res,
    }


@router.get("/review-cases")
def list_payment_review_cases(
    status: Optional[str] = Query("PENDING", description="PENDING, APPROVED, REJECTED, ALL"),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists late or disputed payment cases requiring administrative review."""
    conditions = []
    params = []
    if status and status.upper() != "ALL":
        conditions.append("r.status = ?")
        params.append(status.upper())

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT r.*, r.id AS case_id,
                   r.amount_uzs AS incoming_amount_uzs,
                   o.final_amount_uzs AS expected_amount_uzs,
                   o.plan_id, o.plan_name, o.duration_days, o.card_suffix,
                   u.username, u.first_name, u.last_name
            FROM payment_review_cases r
            JOIN payment_orders o ON r.order_id = o.order_id
            JOIN telegram_users u ON r.user_id = u.user_id
            {where_clause}
            ORDER BY r.created_at DESC
        """, params)
        cases = [dict(row) for row in c.fetchall()]

    return {"ok": True, "cases": cases}


def _approve_late_payment_sync(
    case_id: int,
    notes: str,
    admin_id: int,
    admin_name: str,
) -> Dict[str, Any]:
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT r.*, o.plan_id, o.plan_name, o.duration_days, o.card_suffix
            FROM payment_review_cases r
            JOIN payment_orders o ON r.order_id = o.order_id
            WHERE r.id = ? AND r.status = 'PENDING'
        """, (case_id,))
        case = c.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Pending review case not found")

        order_id = case["order_id"]
        user_id = case["user_id"]
        amount_uzs = case["amount_uzs"]
        plan_id = case["plan_id"]
        plan_name = case["plan_name"]
        duration_days = case["duration_days"]
        card_suffix = case["card_suffix"]
        event_id = case["event_id"]

        # Atomically claim PENDING -> APPROVING so concurrent approve/reject cannot double-grant PRO
        c.execute(
            "UPDATE payment_review_cases SET status = 'APPROVING' WHERE id = ? AND status = 'PENDING'",
            (case_id,),
        )
        conn.commit()
        if (c.rowcount or 0) != 1:
            raise HTTPException(status_code=409, detail="Pending review case already resolved or in progress")

        try:
            c.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
            u_row = c.fetchone()

            base_dt = now_dt
            if u_row and u_row["is_pro"] and u_row["subscription_expires_at"]:
                try:
                    curr_exp = datetime.fromisoformat(u_row["subscription_expires_at"].replace("Z", ""))
                    if curr_exp > now_dt:
                        base_dt = curr_exp
                except Exception:
                    pass

            new_expires_dt = base_dt + timedelta(days=duration_days)
            new_expires_str = new_expires_dt.isoformat()

            execute_batch(conn, [
                (
                    """
                    UPDATE payment_review_cases
                    SET status = 'APPROVED', admin_notes = ?, resolved_by_admin = ?, resolved_at = ?
                    WHERE id = ? AND status = 'APPROVING'
                    """,
                    [notes, admin_name, now_str, case_id],
                ),
                (
                    "UPDATE payment_orders SET status = 'PAID', paid_at = ? WHERE order_id = ? AND status != 'PAID'",
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
                    VALUES (?, 'LATE_PAYMENT_APPROVED', ?, ?)
                    """,
                    [admin_id, f"Case: {case_id}, Order: {order_id}, User: {user_id}, Notes: {notes}", now_str],
                ),
            ])
        except Exception:
            try:
                conn.execute(
                    "UPDATE payment_review_cases SET status = 'PENDING' WHERE id = ? AND status = 'APPROVING'",
                    (case_id,),
                )
                conn.commit()
            except Exception:
                pass
            raise

    try:
        from src.api.deps import invalidate_user_cache
        invalidate_user_cache(user_id)
    except Exception:
        pass

    return {
        "order_id": order_id,
        "user_id": user_id,
        "amount_uzs": amount_uzs,
        "plan_name": plan_name,
        "duration_days": duration_days,
        "expires_at": new_expires_str,
    }


@router.post("/review/{case_id}/approve")
async def approve_late_payment(
    case_id: int,
    req: ResolveReviewRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Manually approves a late payment atomically via execute_batch():
    Marks order PAID, activates user subscription, records ledger transaction.
    """
    admin_name = current_admin["username"]
    res = await asyncio.to_thread(
        _approve_late_payment_sync,
        case_id,
        req.resolved_notes(),
        current_admin["id"],
        admin_name,
    )

    try:
        await send_user_payment_success_notification(
            res["user_id"], res["plan_name"], res["expires_at"], duration_days=res["duration_days"]
        )
        await send_late_payment_approved_alert(
            res["order_id"], res["amount_uzs"], res["user_id"], res["plan_name"], admin_name
        )
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Kechiktirilgan to‘lov tasdiqlandi. Foydalanuvchiga ({res['user_id']}) PRO obuna faollashtirildi.",
        "expires_at": res["expires_at"]
    }


@router.post("/review/{case_id}/reject")
def reject_late_payment(
    case_id: int,
    req: ResolveReviewRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Rejects a review case atomically with administrative explanation."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM payment_review_cases WHERE id = ? AND status = 'PENDING'", (case_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Pending review case not found")

        notes_val = req.resolved_notes()
        execute_batch(conn, [
            (
                """
                UPDATE payment_review_cases
                SET status = 'REJECTED', admin_notes = ?, resolved_by_admin = ?, resolved_at = ?
                WHERE id = ? AND status = 'PENDING'
                """,
                [notes_val, current_admin["username"], now_str, case_id],
            ),
            (
                """
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (?, 'LATE_PAYMENT_REJECTED', ?, ?)
                """,
                [current_admin["id"], f"Case: {case_id}, Notes: {notes_val}", now_str],
            ),
        ])

    return {"ok": True, "message": "Holat bekor qilindi (rad etildi)."}


@router.get("/reconciliation")
def get_reconciliation_report(current_admin: dict = Depends(get_current_admin)):
    """
    Computes financial reconciliation discrepancy report:
    1. Incoming bank notification events
    2. Payment records in ledger
    3. Subscription activations
    4. Unmatched & review cases
    """
    with _get_connection() as conn:
        c = conn.cursor()

        # Bank notification events
        c.execute("""
            SELECT 
                COUNT(*) as total_events,
                COALESCE(SUM(CASE WHEN transaction_type = 'INCOMING' THEN 1 ELSE 0 END), 0) as incoming_events,
                COALESCE(SUM(CASE WHEN transaction_type = 'INCOMING' THEN incoming_amount_uzs ELSE 0 END), 0) as total_incoming_uzs,
                COALESCE(SUM(CASE WHEN status = 'MATCHED' THEN 1 ELSE 0 END), 0) as matched_events,
                COALESCE(SUM(CASE WHEN status = 'UNMATCHED' THEN 1 ELSE 0 END), 0) as unmatched_events,
                COALESCE(SUM(CASE WHEN status = 'LATE_REVIEW' THEN 1 ELSE 0 END), 0) as late_review_events
            FROM payment_events
        """)
        events_summary = dict(c.fetchone() or {})

        # Ledger records
        c.execute("""
            SELECT 
                COUNT(*) as total_ledger_tx,
                COALESCE(SUM(amount_uzs), 0) as total_ledger_uzs
            FROM payment_transactions
        """)
        ledger_summary = dict(c.fetchone() or {})

        # Subscriptions
        c.execute("""
            SELECT 
                COUNT(*) as total_subs,
                COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END), 0) as active_subs,
                COALESCE(SUM(CASE WHEN status = 'MANUAL_GRANT' THEN 1 ELSE 0 END), 0) as manual_grants,
                COALESCE(SUM(CASE WHEN status = 'REVOKED' THEN 1 ELSE 0 END), 0) as revoked_subs
            FROM user_subscriptions
        """)
        sub_summary = dict(c.fetchone() or {})

        # Calculate Discrepancy
        matched_events = int(events_summary.get("matched_events") or 0)
        ledger_count = int(ledger_summary.get("total_ledger_tx") or 0)
        discrepancy_count = abs(matched_events - ledger_count)
        is_balanced = (discrepancy_count == 0)

        c.execute("""
            SELECT
                COUNT(*) as total_stars_orders,
                COALESCE(SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END), 0) as paid_stars_orders,
                COALESCE(SUM(CASE WHEN status = 'PAID' THEN stars_amount ELSE 0 END), 0) as total_stars_revenue
            FROM payment_stars_orders
        """)
        stars_summary = dict(c.fetchone() or {})

    return {
        "ok": True,
        "is_balanced": is_balanced,
        "discrepancy_count": discrepancy_count,
        "events_summary": events_summary,
        "ledger_summary": ledger_summary,
        "subscription_summary": sub_summary,
        "stars_summary": stars_summary,
    }


@router.get("/stars")
def list_stars_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="PENDING, PAID, EXPIRED, FAILED"),
    current_admin: dict = Depends(get_current_admin),
):
    """Lists native Telegram Stars (XTR) payment orders and captures."""
    offset = (page - 1) * limit
    conditions = []
    params = []
    if status:
        conditions.append("s.status = ?")
        params.append(status.strip().upper())
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM payment_stars_orders s {where_clause}", params)
        total_items = int(c.fetchone()[0] or 0)
        c.execute(
            f"""
            SELECT s.*, u.username, u.first_name, u.last_name
            FROM payment_stars_orders s
            LEFT JOIN telegram_users u ON s.user_id = u.user_id
            {where_clause}
            ORDER BY s.created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        )
        orders = [dict(r) for r in c.fetchall()]

    return {
        "ok": True,
        "total": total_items,
        "page": page,
        "limit": limit,
        "orders": orders,
    }


@router.get("/health")
def get_payments_and_mtproto_health(current_admin: dict = Depends(get_current_admin)):
    """Combined observability snapshot for Humo payment reconciliation & MTProto worker health."""
    rec_health = get_payment_reconciliation_health_sync()
    mtproto_status = (
        get_mtproto_manager().get_status()
        if get_mtproto_manager is not None
        else {
            "connection_status": "SERVERLESS_OFFLOADED",
            "monitored_bot": "Humocardbot",
            "active_orders_count": rec_health.get("pending_orders", 0),
            "last_event_at": rec_health.get("last_event_at"),
            "last_payment_at": None,
            "last_error": None,
            "has_telethon": False,
            "is_live_connected": False,
            "can_accept_simulated_events": True,
            "is_ready_for_matching": False,
        }
    )
    return {
        "ok": True,
        "reconciliation": rec_health,
        "mtproto": mtproto_status,
    }
