"""
Admin Order Management Routes.
Supports:
- Filtered order listings across Active, Expired, Paid, Review Required, and Cancelled tabs
- Full order snapshot inspection with payment card and incoming transaction references
- Searching by Telegram ID, Order ID, Username, Amount, and Card suffix
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query

from src.admin.deps import get_current_admin, require_admin_role
from src.db_adapter import fetch_batch_dicts, get_db_connection

router = APIRouter(
    prefix="/api/admin/orders",
    tags=["Admin Orders"],
    dependencies=[Depends(require_admin_role("FINANCE", "SUPPORT"))],
)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")

def _get_connection():
    return get_db_connection(DB_PATH)


@router.get("")
def list_orders(
    tab: str = Query("all", description="active, expired, paid, review_required, cancelled, all"),
    q: Optional[str] = Query(None, description="Search by Telegram ID, Order ID, Username, Amount, or Card suffix"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="created_at, final_amount_uzs"),
    sort_order: str = Query("desc", description="desc, asc"),
    current_admin: dict = Depends(get_current_admin)
):
    """Lists orders filtered by lifecycle tab in 1 batched DB round-trip (zero GET writes)."""
    now_iso = datetime.utcnow().isoformat()
    offset = (page - 1) * limit
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"
    order_col = "o.final_amount_uzs" if sort_by == "final_amount_uzs" else "o.created_at"

    conditions = []
    params = []

    if tab == "active":
        conditions.append("o.status = 'PENDING' AND o.expires_at > ?")
        params.append(now_iso)
    elif tab == "expired":
        conditions.append("(o.status = 'EXPIRED' OR (o.status = 'PENDING' AND o.expires_at <= ?))")
        params.append(now_iso)
    elif tab == "paid":
        conditions.append("o.status = 'PAID'")
    elif tab == "review_required":
        conditions.append("o.status = 'PAYMENT_REVIEW_REQUIRED'")
    elif tab == "cancelled":
        conditions.append("o.status = 'CANCELLED'")

    if q:
        q_clean = f"%{q.strip()}%"
        conditions.append("""(
            o.order_id LIKE ? 
            OR CAST(o.user_id AS TEXT) LIKE ? 
            OR u.username LIKE ? 
            OR u.first_name LIKE ?
            OR CAST(o.final_amount_uzs AS TEXT) LIKE ?
            OR o.card_suffix LIKE ?
        )""")
        params.extend([q_clean, q_clean, q_clean, q_clean, q_clean, q_clean])

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        batches = fetch_batch_dicts(
            conn,
            [
                (
                    """
                    SELECT
                        COUNT(*) AS all_count,
                        SUM(CASE WHEN status = 'PENDING' AND expires_at > ? THEN 1 ELSE 0 END) AS active_count,
                        SUM(CASE WHEN status = 'EXPIRED' OR (status = 'PENDING' AND expires_at <= ?) THEN 1 ELSE 0 END) AS expired_count,
                        SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) AS paid_count,
                        SUM(CASE WHEN status = 'PAYMENT_REVIEW_REQUIRED' THEN 1 ELSE 0 END) AS review_count,
                        SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_count
                    FROM payment_orders
                    """.strip(),
                    [now_iso, now_iso],
                ),
                (
                    f"""
                    SELECT COUNT(*) AS cnt
                    FROM payment_orders o
                    LEFT JOIN telegram_users u ON o.user_id = u.user_id
                    {where_clause}
                    """.strip(),
                    list(params),
                ),
                (
                    f"""
                    SELECT o.*, u.username, u.first_name, u.last_name
                    FROM payment_orders o
                    LEFT JOIN telegram_users u ON o.user_id = u.user_id
                    {where_clause}
                    ORDER BY {order_col} {direction}
                    LIMIT ? OFFSET ?
                    """.strip(),
                    list(params) + [limit, offset],
                ),
            ],
        )

    counts_row = batches[0][0] if batches[0] else {}
    tab_counts = {
        "all": counts_row.get("all_count") or 0,
        "active": counts_row.get("active_count") or 0,
        "expired": counts_row.get("expired_count") or 0,
        "paid": counts_row.get("paid_count") or 0,
        "review_required": counts_row.get("review_count") or 0,
        "cancelled": counts_row.get("cancelled_count") or 0,
    }
    total_items = int(batches[1][0]["cnt"] or 0) if batches[1] else 0
    orders = batches[2]

    return {
        "ok": True,
        "tab": tab,
        "tab_counts": tab_counts,
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": (total_items + limit - 1) // limit if limit else 1,
        "orders": orders
    }


@router.get("/{order_id}")
def get_order_details(order_id: str, current_admin: dict = Depends(get_current_admin)):
    """Returns the full order snapshot, associated user, payment transaction, and raw payment event."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT o.*, u.username, u.first_name, u.last_name
            FROM payment_orders o
            LEFT JOIN telegram_users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
        """, (order_id,))
        order_row = c.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")
        order_data = dict(order_row)

        # Matched financial transaction (if any)
        c.execute("SELECT * FROM payment_transactions WHERE order_id = ?", (order_id,))
        tx_row = c.fetchone()
        order_data["transaction"] = dict(tx_row) if tx_row else None

        # Associated incoming payment event (if any)
        c.execute("SELECT * FROM payment_events WHERE matched_order_id = ?", (order_id,))
        event_row = c.fetchone()
        order_data["payment_event"] = dict(event_row) if event_row else None

        # Review case (if any)
        c.execute("SELECT * FROM payment_review_cases WHERE order_id = ?", (order_id,))
        rev_row = c.fetchone()
        order_data["review_case"] = dict(rev_row) if rev_row else None

    return {"ok": True, "order": order_data}
