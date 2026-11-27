"""
Admin Dashboard & Sales Analytics Routes.
Computes real database-backed KPIs, monetary statistics in UZS, and analytical trend charts.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query

from src.admin.deps import get_current_admin, require_admin_role
from src.analytics.tracker import build_retention_query_stmt, parse_retention_rows
from src.db_adapter import fetch_batch_dicts, get_db_connection
try:
    from src.mtproto.service import get_mtproto_manager
except ImportError:
    get_mtproto_manager = None

router = APIRouter(
    prefix="/api/admin/dashboard",
    tags=["Admin Dashboard"],
    dependencies=[Depends(require_admin_role("FINANCE"))],
)
overview_router = APIRouter(
    prefix="/api/admin/overview",
    tags=["Admin Overview"],
    dependencies=[Depends(require_admin_role("FINANCE"))],
)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def _get_connection():
    return get_db_connection(DB_PATH)


def _kpi_stmt(now_dt: datetime) -> tuple[str, list]:
    now_str = now_dt.isoformat()
    today_str = now_dt.strftime("%Y-%m-%d")
    month_prefix = now_dt.strftime("%Y-%m")
    sql = """
    SELECT
        (SELECT COUNT(*) FROM telegram_users) AS total_users,
        (SELECT COUNT(*) FROM telegram_users WHERE is_pro = 1 AND subscription_expires_at IS NOT NULL AND subscription_expires_at > ?) AS active_subscribers,
        (SELECT COUNT(*) FROM telegram_users WHERE created_at >= ?) AS new_users_today,
        (SELECT COUNT(*) FROM user_subscriptions WHERE created_at >= ?) AS subscriptions_today,
        (SELECT COUNT(*) FROM payment_transactions) AS total_successful_payments,
        (SELECT COALESCE(SUM(amount_uzs), 0) FROM payment_transactions) AS total_revenue_uzs,
        (SELECT COALESCE(SUM(amount_uzs), 0) FROM payment_transactions WHERE created_at >= ?) AS today_revenue_uzs,
        (SELECT COALESCE(SUM(amount_uzs), 0) FROM payment_transactions WHERE created_at LIKE ?) AS month_revenue_uzs,
        (SELECT COUNT(*) FROM telegram_users WHERE is_pro = 0 AND subscription_expires_at IS NOT NULL AND subscription_expires_at <= ?) AS expired_subscriptions,
        (SELECT COUNT(*) FROM payment_orders WHERE status = 'PENDING' AND expires_at > ?) AS pending_orders,
        (SELECT COUNT(*) FROM unmatched_payments WHERE status = 'UNRESOLVED') AS unmatched_payments,
        (SELECT COUNT(*) FROM payment_review_cases WHERE status = 'PENDING') AS review_cases,
        (SELECT COUNT(CASE WHEN status = 'PAID' THEN 1 END) FROM payment_stars_orders) AS stars_payments_count,
        (SELECT COALESCE(SUM(CASE WHEN status = 'PAID' THEN stars_amount ELSE 0 END), 0) FROM payment_stars_orders) AS stars_revenue_xtr
    """.strip()
    params = [now_str, today_str, today_str, today_str, f"{month_prefix}%", now_str, now_str]
    return (sql, params)


def _parse_kpis_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_users": int(row.get("total_users") or 0),
        "active_subscribers": int(row.get("active_subscribers") or 0),
        "new_users_today": int(row.get("new_users_today") or 0),
        "subscriptions_today": int(row.get("subscriptions_today") or 0),
        "total_successful_payments": int(row.get("total_successful_payments") or 0),
        "total_revenue_uzs": int(row.get("total_revenue_uzs") or 0),
        "today_revenue_uzs": int(row.get("today_revenue_uzs") or 0),
        "month_revenue_uzs": int(row.get("month_revenue_uzs") or 0),
        "expired_subscriptions": int(row.get("expired_subscriptions") or 0),
        "pending_orders": int(row.get("pending_orders") or 0),
        "unmatched_payments": int(row.get("unmatched_payments") or 0),
        "review_cases_pending": int(row.get("review_cases") or 0),
        "stars_payments_count": int(row.get("stars_payments_count") or 0),
        "stars_revenue_xtr": int(row.get("stars_revenue_xtr") or 0),
    }


@router.get("/kpi")
def get_dashboard_kpis(current_admin: dict = Depends(get_current_admin)):
    """Returns 14 real DB-backed KPIs in 1 single SQL round-trip (zero GET write side-effects)."""
    now_dt = datetime.utcnow()
    sql, params = _kpi_stmt(now_dt)
    with _get_connection() as conn:
        row = fetch_batch_dicts(conn, [(sql, params)])[0][0]
    return {"ok": True, "kpis": _parse_kpis_row(row)}


@overview_router.get("/boot")
def get_admin_overview_boot(
    range_filter: str = Query("30d", description="today, yesterday, 7d, 30d, 90d"),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Zero-waterfall Admin Executive Overview bootstrap (<= 2 Turso RTs including auth).
    Consolidates KPIs, MTProto health, top-5 orders, DAU/WAU/MAU analytics, cohort retention, and sales charts.
    """
    now_dt = datetime.utcnow()
    today_start = now_dt.strftime("%Y-%m-%d")
    d1_ago = (now_dt - timedelta(days=1)).isoformat()
    d7_ago = (now_dt - timedelta(days=7)).isoformat()
    d14_ago = (now_dt - timedelta(days=14)).isoformat()
    d30_ago = (now_dt - timedelta(days=30)).isoformat()

    if range_filter == "today":
        since_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_filter == "yesterday":
        since_dt = (now_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_filter == "7d":
        since_dt = now_dt - timedelta(days=7)
    elif range_filter == "90d":
        since_dt = now_dt - timedelta(days=90)
    else:
        since_dt = now_dt - timedelta(days=30)
    since_str = since_dt.isoformat()
    until_str = now_dt.isoformat()

    kpi_sql, kpi_params = _kpi_stmt(now_dt)
    ret_sql, ret_params = build_retention_query_stmt()
    stmts = [
        (kpi_sql, kpi_params),
        (
            """
            SELECT o.*, u.username, u.first_name, u.last_name
            FROM payment_orders o
            LEFT JOIN telegram_users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC LIMIT 5
            """.strip(),
            [],
        ),
        (
            """
            SELECT
                COUNT(DISTINCT CASE WHEN ts >= ? THEN user_id END) AS dau,
                COUNT(DISTINCT CASE WHEN ts >= ? THEN user_id END) AS wau,
                COUNT(DISTINCT CASE WHEN ts >= ? THEN user_id END) AS mau
            FROM (
                SELECT user_id, created_at AS ts FROM user_activity_events WHERE created_at >= ?
                UNION ALL
                SELECT user_id, created_at AS ts FROM user_sessions WHERE created_at >= ?
                UNION ALL
                SELECT user_id, last_active_at AS ts FROM telegram_users WHERE last_active_at >= ?
            )
            """.strip(),
            [d1_ago, d7_ago, d30_ago, d30_ago, d30_ago, d30_ago],
        ),
        (
            """
            SELECT event_name, COUNT(*) AS cnt
            FROM user_activity_events
            WHERE created_at >= ?
            GROUP BY event_name
            ORDER BY cnt DESC LIMIT 10
            """.strip(),
            [d14_ago],
        ),
        (ret_sql, ret_params),
        (
            """
            SELECT
                (SELECT COUNT(*) FROM payment_transactions WHERE created_at >= ? AND created_at <= ?) AS tx_count,
                (SELECT COALESCE(SUM(amount_uzs), 0) FROM payment_transactions WHERE created_at >= ? AND created_at <= ?) AS total_revenue,
                (SELECT COUNT(*) FROM payment_orders WHERE created_at >= ? AND created_at <= ?) AS total_orders,
                (SELECT COALESCE(SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END), 0) FROM payment_orders WHERE created_at >= ? AND created_at <= ?) AS paid_orders
            """.strip(),
            [since_str, until_str] * 4,
        ),
        (
            """
            SELECT substr(created_at, 1, 10) AS day_str, COUNT(*) AS cnt, COALESCE(SUM(amount_uzs), 0) AS rev
            FROM payment_transactions
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY day_str
            ORDER BY day_str ASC
            """.strip(),
            [since_str, until_str],
        ),
    ]

    with _get_connection() as conn:
        batches = fetch_batch_dicts(conn, stmts)

    kpis = _parse_kpis_row(batches[0][0] if batches[0] else {})
    recent_orders = batches[1]
    d_row = batches[2][0] if batches[2] else {}
    dau = int(d_row.get("dau") or 0)
    wau = int(d_row.get("wau") or 0)
    mau = int(d_row.get("mau") or 0)
    feat_list = [{"event": r["event_name"], "count": int(r["cnt"] or 0)} for r in batches[3]]
    analytics = {
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "total_users": kpis["total_users"],
        "new_users_today": kpis["new_users_today"],
        "engagement_ratio_pct": round((dau / mau * 100.0), 1) if mau > 0 else 0.0,
        "feature_breakdown": feat_list,
        "feature_distribution": {f["event"]: f["count"] for f in feat_list},
    }
    retention = parse_retention_rows(batches[4])

    s_row = batches[5][0] if batches[5] else {}
    tx_count = int(s_row.get("tx_count") or 0)
    total_rev = int(s_row.get("total_revenue") or 0)
    tot_orders = int(s_row.get("total_orders") or 0)
    paid_orders = int(s_row.get("paid_orders") or 0)
    sales_analytics = {
        "range_filter": range_filter,
        "summary": {
            "total_revenue_uzs": total_rev,
            "transaction_count": tx_count,
            "average_transaction_uzs": round(total_rev / tx_count) if tx_count > 0 else 0,
            "conversion_rate_pct": round((paid_orders / tot_orders * 100.0), 1) if tot_orders > 0 else 0.0,
        },
        "daily_chart": [{"date": r["day_str"], "count": r["cnt"], "revenue_uzs": r["rev"]} for r in batches[6]],
    }

    mtproto_status = (
        get_mtproto_manager().get_status()
        if get_mtproto_manager is not None
        else {"connection_status": "SERVERLESS_OFFLOADED", "monitored_bot": "Humocardbot"}
    )

    return {
        "ok": True,
        "kpis": kpis,
        "mtproto": mtproto_status,
        "recent_orders": recent_orders,
        "analytics": analytics,
        "retention": retention,
        "sales_analytics": sales_analytics,
        "meta_today": today_start,
    }


@router.get("/sales-analytics")
def get_sales_analytics(
    range_filter: str = Query("7d", description="today, yesterday, 7d, 30d, 90d, custom"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD for custom range"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD for custom range"),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Returns time-filtered sales analytics, daily revenue breakdowns, plan distributions,
    average order value, and conversion rates computed exclusively from actual records.
    """
    now_dt = datetime.utcnow()

    # Determine date window
    if range_filter == "today":
        since_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        until_dt = now_dt
    elif range_filter == "yesterday":
        yesterday_dt = now_dt - timedelta(days=1)
        since_dt = yesterday_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        until_dt = yesterday_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif range_filter == "30d":
        since_dt = now_dt - timedelta(days=30)
        until_dt = now_dt
    elif range_filter == "90d":
        since_dt = now_dt - timedelta(days=90)
        until_dt = now_dt
    elif range_filter == "custom" and start_date:
        since_dt = datetime.strptime(start_date, "%Y-%m-%d")
        until_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59) if end_date else now_dt
    else:  # Default 7d
        since_dt = now_dt - timedelta(days=7)
        until_dt = now_dt

    since_str = since_dt.isoformat()
    until_str = until_dt.isoformat()

    with _get_connection() as conn:
        c = conn.cursor()

        # 1. Total successful payments & revenue in range
        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount_uzs), 0)
            FROM payment_transactions
            WHERE created_at >= ? AND created_at <= ?
        """, (since_str, until_str))
        p_row = c.fetchone()
        tx_count = p_row[0]
        total_revenue = p_row[1]

        avg_transaction_val = round(total_revenue / tx_count) if tx_count > 0 else 0

        # 2. Daily revenue chart points
        c.execute("""
            SELECT substr(created_at, 1, 10) as day_str, COUNT(*) as cnt, COALESCE(SUM(amount_uzs), 0) as rev
            FROM payment_transactions
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY day_str
            ORDER BY day_str ASC
        """, (since_str, until_str))
        daily_points = [{"date": r["day_str"], "count": r["cnt"], "revenue_uzs": r["rev"]} for r in c.fetchall()]

        # 3. Plan breakdown
        c.execute("""
            SELECT plan_id, COUNT(*) as cnt, COALESCE(SUM(amount_uzs), 0) as rev
            FROM payment_transactions
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY plan_id
        """, (since_str, until_str))
        plan_breakdown = [{"plan_id": r["plan_id"], "count": r["cnt"], "revenue_uzs": r["rev"]} for r in c.fetchall()]

        # 4. Conversion & Failure rates
        # Total orders created in range
        c.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_orders,
                SUM(CASE WHEN status = 'EXPIRED' THEN 1 ELSE 0 END) as expired_orders,
                SUM(CASE WHEN status = 'PAYMENT_REVIEW_REQUIRED' THEN 1 ELSE 0 END) as review_orders
            FROM payment_orders
            WHERE created_at >= ? AND created_at <= ?
        """, (since_str, until_str))
        ord_stats = c.fetchone()
        tot_orders = ord_stats["total_orders"] or 0
        paid_orders = ord_stats["paid_orders"] or 0
        expired_orders = ord_stats["expired_orders"] or 0
        review_orders = ord_stats["review_orders"] or 0

        conversion_rate = round((paid_orders / tot_orders * 100), 1) if tot_orders > 0 else 0.0
        failure_rate = round((expired_orders / tot_orders * 100), 1) if tot_orders > 0 else 0.0

        # 5. New vs renewals
        c.execute("""
            SELECT COUNT(DISTINCT user_id) FROM payment_transactions
            WHERE created_at >= ? AND created_at <= ?
            AND user_id IN (
                SELECT user_id FROM payment_transactions WHERE created_at < ?
            )
        """, (since_str, until_str, since_str))
        renewal_users = c.fetchone()[0]
        new_sub_users = max(0, tx_count - renewal_users)

    return {
        "ok": True,
        "range_filter": range_filter,
        "period": {"since": since_str, "until": until_str},
        "summary": {
            "total_revenue_uzs": total_revenue,
            "transaction_count": tx_count,
            "average_transaction_uzs": avg_transaction_val,
            "conversion_rate_pct": conversion_rate,
            "failure_rate_pct": failure_rate,
            "new_subscriptions_count": new_sub_users,
            "renewals_count": renewal_users
        },
        "daily_chart": daily_points,
        "plan_breakdown": plan_breakdown,
        "order_funnel": {
            "created": tot_orders,
            "paid": paid_orders,
            "expired": expired_orders,
            "review": review_orders
        }
    }
