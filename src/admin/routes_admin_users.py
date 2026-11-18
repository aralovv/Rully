"""
Admin User Management Routes.
Implements:
- Full user listing with search, filtering, and pagination
- Deep user profile with subscription, financial, and activity histories
- Block / Unblock controls with audit logging
- Manual subscription grants (14/30 days) without creating fake financial revenue
- Manual subscription revocations with immediate access cutoff
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin
from src.analytics.tracker import classify_user_activity
from src.security.telegram_notifier import send_user_subscription_granted_notification

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


class BlockUserRequest(BaseModel):
    reason: str = Field(..., description="Administrative reason for blocking the user")


class GrantSubscriptionRequest(BaseModel):
    duration_days: int = Field(..., description="Subscription duration to grant (14 or 30)")
    reason: str = Field(..., description="Reason for granting subscription")


class RevokeSubscriptionRequest(BaseModel):
    reason: str = Field(..., description="Reason for revoking active subscription")


@router.get("")
async def list_users(
    q: Optional[str] = Query(None, description="Search by Telegram ID, username, or name"),
    subscription_status: Optional[str] = Query("all", description="all, pro, free"),
    is_blocked: Optional[int] = Query(None, description="0 (active) or 1 (blocked)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="created_at, last_active_at, user_id"),
    sort_order: str = Query("desc", description="desc, asc"),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists users with search, filters, pagination, and real-time revenue summaries."""
    offset = (page - 1) * limit
    allowed_sort_fields = {"created_at": "u.created_at", "last_active_at": "u.last_active_at", "user_id": "u.user_id"}
    order_col = allowed_sort_fields.get(sort_by, "u.created_at")
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"

    conditions = []
    params = []

    if q:
        q_clean = f"%{q.strip()}%"
        conditions.append("(u.username LIKE ? OR u.first_name LIKE ? OR CAST(u.user_id AS TEXT) LIKE ?)")
        params.extend([q_clean, q_clean, q_clean])

    if subscription_status == "pro":
        conditions.append("u.is_pro = 1 AND u.subscription_expires_at > datetime('now')")
    elif subscription_status == "free":
        conditions.append("(u.is_pro = 0 OR u.subscription_expires_at <= datetime('now') OR u.subscription_expires_at IS NULL)")

    if is_blocked is not None:
        conditions.append("u.is_blocked = ?")
        params.append(is_blocked)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()

        # Count total
        c.execute(f"SELECT COUNT(*) FROM telegram_users u {where_clause}", params)
        total_count = c.fetchone()[0]

        # Fetch page items
        query = f"""
            SELECT 
                u.*,
                COALESCE(p.pay_count, 0) as total_payments_count,
                COALESCE(p.total_revenue, 0) as total_revenue_uzs
            FROM telegram_users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) as pay_count, SUM(amount_uzs) as total_revenue
                FROM payment_transactions
                GROUP BY user_id
            ) p ON u.user_id = p.user_id
            {where_clause}
            ORDER BY {order_col} {direction}
            LIMIT ? OFFSET ?
        """
        c.execute(query, params + [limit, offset])
        rows = c.fetchall()

        items = []
        for r in rows:
            u_dict = dict(r)
            # Add explainable activity classification
            classification = classify_user_activity(u_dict["user_id"], conn)
            u_dict["activity_classification"] = classification
            items.append(u_dict)

    return {
        "ok": True,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if limit else 1,
        "users": items
    }


@router.get("/{user_id}")
async def get_user_profile(user_id: int, current_admin: dict = Depends(get_current_admin)):
    """Returns complete user dossier including subscriptions, payments, orders, and activity telemetry."""
    with _get_connection() as conn:
        c = conn.cursor()

        # 1. Base User Record
        c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        user_data = dict(user_row)

        # 2. Activity Classification
        user_data["activity_classification"] = classify_user_activity(user_id, conn)

        # 3. Subscription History
        c.execute("""
            SELECT * FROM user_subscriptions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        subscriptions = [dict(r) for r in c.fetchall()]

        # 4. Payment History (Verified transactions)
        c.execute("""
            SELECT * FROM payment_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        payments = [dict(r) for r in c.fetchall()]

        # 5. Order History
        c.execute("""
            SELECT * FROM payment_orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        orders = [dict(r) for r in c.fetchall()]

        # 6. Recent Activity Telemetry Events (Last 50)
        c.execute("""
            SELECT * FROM user_activity_events 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 50
        """, (user_id,))
        activity_events = [dict(r) for r in c.fetchall()]

        # 7. Exam Results summary
        c.execute("""
            SELECT COUNT(*) as total_exams,
                   SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_exams,
                   AVG(percentage) as avg_score
            FROM exam_results WHERE user_id = ?
        """, (user_id,))
        exam_stat = dict(c.fetchone() or {})

    return {
        "ok": True,
        "user": user_data,
        "subscriptions": subscriptions,
        "payments": payments,
        "orders": orders,
        "activity_events": activity_events,
        "exam_stats": exam_stat
    }


@router.post("/{user_id}/block")
async def block_user(user_id: int, req: BlockUserRequest, current_admin: dict = Depends(get_current_admin)):
    """Blocks a user and records administrative audit details."""
    now_str = datetime.utcnow().isoformat()
    admin_name = current_admin["username"]

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE telegram_users 
            SET is_blocked = 1, block_reason = ?, blocked_at = ?, blocked_by = ?
            WHERE user_id = ?
        """, (req.reason.strip(), now_str, admin_name, user_id))

        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'USER_BLOCKED', ?, ?)
        """, (current_admin["id"], f"User: {user_id}, Reason: {req.reason}", now_str))

        c.execute("""
            INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
            VALUES (?, 'USER_BLOCKED', ?, ?)
        """, (user_id, f'{{"blocked_by": "{admin_name}", "reason": "{req.reason}"}}', now_str))

        conn.commit()

    return {"ok": True, "message": f"Foydalanuvchi ({user_id}) muvaffaqiyatli bloklandi."}


@router.post("/{user_id}/unblock")
async def unblock_user(user_id: int, current_admin: dict = Depends(get_current_admin)):
    """Unblocks a user and restores their service access."""
    now_str = datetime.utcnow().isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE telegram_users 
            SET is_blocked = 0, block_reason = NULL, blocked_at = NULL, blocked_by = NULL
            WHERE user_id = ?
        """, (user_id,))

        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'USER_UNBLOCKED', ?, ?)
        """, (current_admin["id"], f"User: {user_id}", now_str))

        c.execute("""
            INSERT INTO user_activity_events (user_id, event_name, created_at)
            VALUES (?, 'USER_UNBLOCKED', ?)
        """, (user_id, now_str))

        conn.commit()

    return {"ok": True, "message": f"Foydalanuvchi ({user_id}) blokdan chiqarildi."}


@router.post("/{user_id}/grant-subscription")
async def grant_subscription(
    user_id: int,
    req: GrantSubscriptionRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Manually grants or extends a subscription (14 or 30 days).
    CRITICAL: Does NOT create fake payment transactions or fake revenue.
    """
    if req.duration_days not in [14, 30]:
        raise HTTPException(status_code=400, detail="Duration must be 14 or 30 days.")

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()
    plan_id = "pro_14" if req.duration_days == 14 else "pro_30"
    plan_name = f"{req.duration_days} kunlik PRO (Admin sovg‘asi)"

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        base_dt = now_dt
        if row["is_pro"] and row["subscription_expires_at"]:
            try:
                curr_exp = datetime.fromisoformat(row["subscription_expires_at"].replace("Z", ""))
                if curr_exp > now_dt:
                    base_dt = curr_exp
            except Exception:
                pass

        new_expires_dt = base_dt + timedelta(days=req.duration_days)
        new_expires_str = new_expires_dt.isoformat()

        # Update telegram_users
        c.execute("""
            UPDATE telegram_users 
            SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
            WHERE user_id = ?
        """, (plan_id, new_expires_str, user_id))

        # Record in user_subscriptions with status 'MANUAL_GRANT' and price 0 to preserve financial reconciliation
        c.execute("""
            INSERT INTO user_subscriptions (
                user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
            ) VALUES (?, ?, ?, ?, 0, 'MANUAL_GRANT', ?, ?)
        """, (user_id, plan_id, plan_name, req.duration_days, now_str, new_expires_str))

        # Record audit log
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'MANUAL_SUBSCRIPTION_GRANTED', ?, ?)
        """, (current_admin["id"], f"User: {user_id}, Days: {req.duration_days}, Reason: {req.reason}", now_str))

        conn.commit()

    # Deliver in-bot notification to user
    try:
        await send_user_subscription_granted_notification(
            user_id=user_id,
            duration_days=req.duration_days,
            expires_at=new_expires_str
        )
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"Foydalanuvchiga {req.duration_days} kunlik PRO obuna muvaffaqiyatli taqdim etildi.",
        "expires_at": new_expires_str
    }


@router.post("/{user_id}/revoke-subscription")
async def revoke_subscription(
    user_id: int,
    req: RevokeSubscriptionRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Manually revokes an active subscription immediately.
    Preserves historical records and logs audit reason.
    """
    now_str = datetime.utcnow().isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT is_pro FROM telegram_users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        # Set user back to free tier
        c.execute("""
            UPDATE telegram_users 
            SET is_pro = 0, subscription_tier = 'free'
            WHERE user_id = ?
        """, (user_id,))

        # Update active subscriptions to REVOKED
        c.execute("""
            UPDATE user_subscriptions 
            SET status = 'REVOKED' 
            WHERE user_id = ? AND status = 'ACTIVE'
        """, (user_id,))

        # Audit log
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'MANUAL_SUBSCRIPTION_REVOKED', ?, ?)
        """, (current_admin["id"], f"User: {user_id}, Reason: {req.reason}", now_str))

        conn.commit()

    return {"ok": True, "message": f"Foydalanuvchining ({user_id}) obunasi muvaffaqiyatli bekor qilindi."}
