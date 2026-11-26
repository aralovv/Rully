"""
Admin Dashboard & Sales Analytics Routes.
Computes real database-backed KPIs, monetary statistics in UZS, and analytical trend charts.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query

from src.admin.deps import get_current_admin
from src.payments.order_manager import expire_stale_orders

router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin Dashboard"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


@router.get("/kpi")
def get_dashboard_kpis(current_admin: dict = Depends(get_current_admin)):
    """
    Returns 10 real database-backed KPI metrics for the executive overview.
    All monetary amounts are represented in Uzbek So'm (UZS).
    Optimized to execute as a single atomic batch query for sub-second latency.
    """
    expire_stale_orders()
    now_dt = datetime.utcnow()
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
        (SELECT COUNT(*) FROM payment_review_cases WHERE status = 'PENDING') AS review_cases
    """
    params = [
        now_str,            # active_subscribers
        today_str,          # new_users_today
        today_str,          # subscriptions_today
        today_str,          # today_revenue_uzs
        f"{month_prefix}%", # month_revenue_uzs
        now_str,            # expired_subscriptions
        now_str             # pending_orders
    ]

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(sql, params)
        row = c.fetchone()

        total_users = row[0]
        active_subscribers = row[1]
        new_users_today = row[2]
        subscriptions_today = row[3]
        total_successful_payments = row[4]
        total_revenue_uzs = row[5]
        today_revenue_uzs = row[6]
        month_revenue_uzs = row[7]
        expired_subscriptions = row[8]
        pending_orders = row[9]
        unmatched_payments = row[10]
        review_cases = row[11]

    return {
        "ok": True,
        "kpis": {
            "total_users": total_users,
            "active_subscribers": active_subscribers,
            "new_users_today": new_users_today,
            "subscriptions_today": subscriptions_today,
            "total_successful_payments": total_successful_payments,
            "total_revenue_uzs": total_revenue_uzs,
            "today_revenue_uzs": today_revenue_uzs,
            "month_revenue_uzs": month_revenue_uzs,
            "expired_subscriptions": expired_subscriptions,
            "pending_orders": pending_orders,
            "unmatched_payments": unmatched_payments,
            "review_cases_pending": review_cases
        }
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
