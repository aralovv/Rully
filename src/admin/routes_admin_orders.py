"""
Admin Order Management Routes.
Supports:
- Filtered order listings across Active, Expired, Paid, Review Required, and Cancelled tabs
- Full order snapshot inspection with payment card and incoming transaction references
- Searching by Telegram ID, Order ID, Username, Amount, and Card suffix
"""

import os
import sqlite3
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query

from src.admin.deps import get_current_admin
from src.payments.order_manager import expire_stale_orders

router = APIRouter(prefix="/api/admin/orders", tags=["Admin Orders"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

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
    """Lists orders filtered by lifecycle tab with search, tab counters, and pagination."""
    expire_stale_orders()
    offset = (page - 1) * limit
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"
    order_col = "o.final_amount_uzs" if sort_by == "final_amount_uzs" else "o.created_at"

    conditions = []
    params = []

    # Tab filter
    if tab == "active":
        conditions.append("o.status = 'PENDING' AND o.expires_at > datetime('now')")
    elif tab == "expired":
        conditions.append("(o.status = 'EXPIRED' OR (o.status = 'PENDING' AND o.expires_at <= datetime('now')))")
    elif tab == "paid":
        conditions.append("o.status = 'PAID'")
    elif tab == "review_required":
        conditions.append("o.status = 'PAYMENT_REVIEW_REQUIRED'")
    elif tab == "cancelled":
        conditions.append("o.status = 'CANCELLED'")

    # Search filter
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
        c = conn.cursor()

        # Get counts for tabs
        c.execute("""
            SELECT 
                COUNT(*) as all_count,
                SUM(CASE WHEN status = 'PENDING' AND expires_at > datetime('now') THEN 1 ELSE 0 END) as active_count,
                SUM(CASE WHEN status = 'EXPIRED' OR (status = 'PENDING' AND expires_at <= datetime('now')) THEN 1 ELSE 0 END) as expired_count,
                SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'PAYMENT_REVIEW_REQUIRED' THEN 1 ELSE 0 END) as review_count,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled_count
            FROM payment_orders
        """)
        counts_row = c.fetchone()
        tab_counts = {
            "all": counts_row["all_count"] or 0,
            "active": counts_row["active_count"] or 0,
            "expired": counts_row["expired_count"] or 0,
            "paid": counts_row["paid_count"] or 0,
            "review_required": counts_row["review_count"] or 0,
            "cancelled": counts_row["cancelled_count"] or 0
        }

        # Filtered total
        count_query = f"""
            SELECT COUNT(*) 
            FROM payment_orders o 
            LEFT JOIN telegram_users u ON o.user_id = u.user_id 
            {where_clause}
        """
        c.execute(count_query, params)
        total_items = c.fetchone()[0]

        # Fetch page items
        data_query = f"""
            SELECT o.*, u.username, u.first_name, u.last_name
            FROM payment_orders o
            LEFT JOIN telegram_users u ON o.user_id = u.user_id
            {where_clause}
            ORDER BY {order_col} {direction}
            LIMIT ? OFFSET ?
        """
        c.execute(data_query, params + [limit, offset])
        orders = [dict(r) for r in c.fetchall()]

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
