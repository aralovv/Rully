"""
Admin Payment Reconciliation, Unmatched Payments, and Review Queue Routes.
Supports:
- Verified transaction ledger inspection
- Late payment review queue resolution (manual approval or rejection)
- Unmatched payment audit and linking
- Financial reconciliation discrepancy reporting
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin
from src.security.telegram_notifier import send_user_payment_success_notification, send_late_payment_approved_alert

router = APIRouter(prefix="/api/admin/payments", tags=["Admin Payments & Reconciliation"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


class ResolveReviewRequest(BaseModel):
    notes: Optional[str] = Field("", description="Admin resolution notes")


class ResolveUnmatchedRequest(BaseModel):
    status: str = Field("RESOLVED_REFUNDED", description="RESOLVED_LINKED, RESOLVED_REFUNDED, IGNORED")
    notes: str = Field(..., description="Resolution explanation")


@router.get("/transactions")
async def list_payment_transactions(
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
async def list_unmatched_payments(
    status: Optional[str] = Query(None, description="UNRESOLVED, RESOLVED_LINKED, RESOLVED_REFUNDED, IGNORED"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists incoming payments from Humocardbot that could not be matched against active orders."""
    offset = (page - 1) * limit
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM unmatched_payments {where_clause}", params)
        total_items = c.fetchone()[0]

        c.execute(f"""
            SELECT u.*, e.raw_message, e.source_chat
            FROM unmatched_payments u
            LEFT JOIN payment_events e ON u.event_id = e.id
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        unmatched = [dict(r) for r in c.fetchall()]

    return {
        "ok": True,
        "total": total_items,
        "page": page,
        "limit": limit,
        "unmatched": unmatched
    }


@router.post("/unmatched/{unmatched_id}/resolve")
async def resolve_unmatched_payment(
    unmatched_id: int,
    req: ResolveUnmatchedRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Resolves an unmatched payment case with administrative audit notes."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE unmatched_payments
            SET status = ?, resolution_notes = ?, resolved_by_admin = ?, resolved_at = ?
            WHERE id = ?
        """, (req.status, req.notes, current_admin["username"], now_str, unmatched_id))

        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Unmatched payment record not found")

        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'UNMATCHED_PAYMENT_RESOLVED', ?, ?)
        """, (current_admin["id"], f"ID: {unmatched_id}, Status: {req.status}, Notes: {req.notes}", now_str))

        conn.commit()

    return {"ok": True, "message": "Holat muvaffaqiyatli hal qilindi."}


@router.get("/review-cases")
async def list_payment_review_cases(
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
            SELECT r.*, o.plan_id, o.plan_name, o.duration_days, o.card_suffix,
                   u.username, u.first_name, u.last_name
            FROM payment_review_cases r
            JOIN payment_orders o ON r.order_id = o.order_id
            JOIN telegram_users u ON r.user_id = u.user_id
            {where_clause}
            ORDER BY r.created_at DESC
        """, params)
        cases = [dict(row) for row in c.fetchall()]

    return {"ok": True, "cases": cases}


@router.post("/review/{case_id}/approve")
async def approve_late_payment(
    case_id: int,
    req: ResolveReviewRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Manually approves a late payment:
    Atomically marks order PAID, activates user subscription, records ledger transaction.
    """
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    admin_name = current_admin["username"]

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

        # 1. Update review case
        c.execute("""
            UPDATE payment_review_cases
            SET status = 'APPROVED', admin_notes = ?, resolved_by_admin = ?, resolved_at = ?
            WHERE id = ?
        """, (req.notes, admin_name, now_str, case_id))

        # 2. Update order to PAID
        c.execute("UPDATE payment_orders SET status = 'PAID', paid_at = ? WHERE order_id = ?", (now_str, order_id))

        # 3. Update payment event to MATCHED
        c.execute("UPDATE payment_events SET status = 'MATCHED', matched_order_id = ? WHERE id = ?", (order_id, event_id))

        # 4. Insert into payment_transactions financial ledger
        c.execute("""
            INSERT INTO payment_transactions (
                order_id, user_id, event_id, amount_uzs, plan_id, card_suffix, payment_timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, event_id, amount_uzs, plan_id, card_suffix, now_str, now_str))

        # 5. Activate user subscription
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

        c.execute("""
            UPDATE telegram_users 
            SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
            WHERE user_id = ?
        """, (plan_id, new_expires_str, user_id))

        c.execute("""
            INSERT INTO user_subscriptions (
                user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """, (user_id, plan_id, plan_name, duration_days, amount_uzs, now_str, new_expires_str))

        # 6. Audit log
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'LATE_PAYMENT_APPROVED', ?, ?)
        """, (current_admin["id"], f"Case: {case_id}, Order: {order_id}, User: {user_id}, Notes: {req.notes}", now_str))

        conn.commit()

    # Notify user and orders group
    try:
        await send_user_payment_success_notification(user_id, plan_name, new_expires_str, duration_days=duration_days)
        await send_late_payment_approved_alert(order_id, amount_uzs, user_id, plan_name, admin_name)
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Kechiktirilgan to‘lov tasdiqlandi. Foydalanuvchiga ({user_id}) PRO obuna faollashtirildi.",
        "expires_at": new_expires_str
    }


@router.post("/review/{case_id}/reject")
async def reject_late_payment(
    case_id: int,
    req: ResolveReviewRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Rejects a review case with administrative explanation."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE payment_review_cases
            SET status = 'REJECTED', admin_notes = ?, resolved_by_admin = ?, resolved_at = ?
            WHERE id = ? AND status = 'PENDING'
        """, (req.notes, current_admin["username"], now_str, case_id))

        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pending review case not found")

        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'LATE_PAYMENT_REJECTED', ?, ?)
        """, (current_admin["id"], f"Case: {case_id}, Notes: {req.notes}", now_str))

        conn.commit()

    return {"ok": True, "message": "Holat bekor qilindi (rad etildi)."}


@router.get("/reconciliation")
async def get_reconciliation_report(current_admin: dict = Depends(get_current_admin)):
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
                SUM(CASE WHEN transaction_type = 'INCOMING' THEN 1 ELSE 0 END) as incoming_events,
                COALESCE(SUM(CASE WHEN transaction_type = 'INCOMING' THEN incoming_amount_uzs ELSE 0 END), 0) as total_incoming_uzs,
                SUM(CASE WHEN status = 'MATCHED' THEN 1 ELSE 0 END) as matched_events,
                SUM(CASE WHEN status = 'UNMATCHED' THEN 1 ELSE 0 END) as unmatched_events,
                SUM(CASE WHEN status = 'LATE_REVIEW' THEN 1 ELSE 0 END) as late_review_events
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
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_subs,
                SUM(CASE WHEN status = 'MANUAL_GRANT' THEN 1 ELSE 0 END) as manual_grants,
                SUM(CASE WHEN status = 'REVOKED' THEN 1 ELSE 0 END) as revoked_subs
            FROM user_subscriptions
        """)
        sub_summary = dict(c.fetchone() or {})

        # Calculate Discrepancy
        matched_events = events_summary.get("matched_events", 0)
        ledger_count = ledger_summary.get("total_ledger_tx", 0)
        discrepancy_count = abs(matched_events - ledger_count)
        is_balanced = (discrepancy_count == 0)

    return {
        "ok": True,
        "is_balanced": is_balanced,
        "discrepancy_count": discrepancy_count,
        "events_summary": events_summary,
        "ledger_summary": ledger_summary,
        "subscription_summary": sub_summary
    }
