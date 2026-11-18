"""
Admin Audit Trail & System Health Routes.
"""

import os
import sqlite3
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query

from src.admin.deps import get_current_admin
from src.mtproto.service import get_mtproto_manager
from src.payments.order_manager import get_active_orders_count

router = APIRouter(prefix="/api/admin/system", tags=["Admin System Health & Logs"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action name"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_admin: dict = Depends(get_current_admin)
):
    """Returns chronological administrative audit logs."""
    offset = (page - 1) * limit
    conditions = []
    params = []

    if action:
        conditions.append("action = ?")
        params.append(action)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM admin_audit_logs {where_clause}", params)
        total_items = c.fetchone()[0]

        c.execute(f"""
            SELECT * FROM admin_audit_logs 
            {where_clause}
            ORDER BY id DESC 
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        logs = [dict(r) for r in c.fetchall()]

    return {
        "ok": True,
        "total": total_items,
        "page": page,
        "limit": limit,
        "logs": logs
    }


@router.get("/health")
async def get_system_health(current_admin: dict = Depends(get_current_admin)):
    """Performs deep database integrity checks and collects system health diagnostics."""
    t0 = time.time()
    with _get_connection() as conn:
        c = conn.cursor()

        # Integrity Check
        c.execute("PRAGMA integrity_check;")
        int_res = c.fetchall()
        integrity_ok = (len(int_res) == 1 and int_res[0][0] == "ok")

        # Foreign Key Violations
        c.execute("PRAGMA foreign_key_check;")
        fk_violations = len(c.fetchall())

        # Table row counts
        tables_to_check = [
            "telegram_users", "user_subscriptions", "payment_orders",
            "payment_events", "payment_transactions", "unmatched_payments",
            "payment_review_cases", "user_activity_events"
        ]
        counts = {}
        for tbl in tables_to_check:
            c.execute(f"SELECT COUNT(*) FROM {tbl}")
            counts[tbl] = c.fetchone()[0]

    db_latency_ms = round((time.time() - t0) * 1000, 2)
    mtproto = get_mtproto_manager().get_status()
    active_orders = get_active_orders_count()

    is_overall_healthy = integrity_ok and fk_violations == 0

    return {
        "ok": True,
        "overall_status": "HEALTHY" if is_overall_healthy else "WARNING",
        "database": {
            "integrity_check": "ok" if integrity_ok else str(int_res),
            "foreign_key_violations": fk_violations,
            "latency_ms": db_latency_ms,
            "table_counts": counts
        },
        "mtproto": {
            "status": mtproto["connection_status"],
            "monitored_bot": mtproto["monitored_bot"],
            "last_event_at": mtproto["last_event_at"],
            "last_payment_at": mtproto["last_payment_at"],
            "last_error": mtproto["last_error"]
        },
        "payment_engine": {
            "active_orders_count": active_orders,
            "matching_pipeline": "ACTIVE" if active_orders > 0 else "IDLE_ZERO_ORDERS"
        }
    }
