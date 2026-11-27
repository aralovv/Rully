"""
Real User Activity Analytics & Telemetry Engine.
Tracks actual user events and computes:
- DAU, WAU, MAU, DAU/MAU engagement ratio
- Transparent, explainable activity classification
- Cohort retention (D1, D7, D30)
- Subscription conversion rates
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


def log_user_event(
    user_id: int,
    event_name: str,
    event_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """Logs a discrete user action to user_activity_events and updates user last_active_at."""
    now_str = datetime.utcnow().isoformat()
    data_json = json.dumps(event_data) if event_data else None

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_activity_events (user_id, event_name, event_data, ip_address, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, event_name, data_json, ip_address, user_agent, now_str))

        # Update last_active_at on telegram_users
        c.execute("UPDATE telegram_users SET last_active_at = ? WHERE user_id = ?", (now_str, user_id))
        conn.commit()
        return True


def _build_activity_classification(
    events_14d: int,
    active_days_14d: int,
    events_prior: int,
    is_pro: bool,
) -> Dict[str, Any]:
    if active_days_14d >= 7 or events_14d >= 25:
        category = "Highly Active"
        badge_color = "emerald"
        explanation = f"Juda faol — So‘nggi 14 kunda {active_days_14d} kun faol bo‘lgan, {events_14d} ta harakat."
    elif active_days_14d >= 3 or events_14d >= 8:
        category = "Active"
        badge_color = "blue"
        explanation = f"Faol — So‘nggi 14 kunda {active_days_14d} kun faol, {events_14d} ta harakat."
    elif active_days_14d >= 1 or events_14d >= 1:
        category = "Occasionally Active"
        badge_color = "amber"
        explanation = f"Vaqti-vaqti bilan — So‘nggi 14 kunda {active_days_14d} kun faol."
    elif events_prior > 0:
        category = "At Risk"
        badge_color = "orange"
        explanation = "Xavf ostida — So‘nggi 14 kunda harakat yo‘q, lekin oxirgi oyda kirgan."
    else:
        category = "Inactive"
        badge_color = "gray"
        explanation = "Nofaol — 30 kundan ortiq muddat davomida tizimda harakat qayd etilmagan."

    return {
        "category": category,
        "segment": category,
        "badge_color": badge_color,
        "explanation": explanation,
        "active_days_14d": int(active_days_14d or 0),
        "events_14d": int(events_14d or 0),
        "is_pro": bool(is_pro),
    }


def classify_users_activity_batch(user_ids: List[int], conn: Optional[sqlite3.Connection] = None) -> Dict[int, Dict[str, Any]]:
    """Classifies a page of users in O(1) batched SQL queries (eliminates 3N per-user queries)."""
    clean_ids = [int(uid) for uid in user_ids if uid is not None]
    if not clean_ids:
        return {}

    should_close = False
    if conn is None:
        conn = _get_connection()
        should_close = True

    try:
        now_dt = datetime.utcnow()
        d14_ago = (now_dt - timedelta(days=14)).isoformat()
        d30_ago = (now_dt - timedelta(days=30)).isoformat()
        placeholders = ",".join("?" * len(clean_ids))
        c = conn.cursor()

        c.execute(f"SELECT user_id, is_pro FROM telegram_users WHERE user_id IN ({placeholders})", clean_ids)
        pro_map = {int(r[0]): bool(r[1]) for r in c.fetchall()}

        c.execute(
            f"""
            SELECT
                user_id,
                COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0) AS events_14d,
                COUNT(DISTINCT CASE WHEN created_at >= ? THEN substr(created_at, 1, 10) END) AS active_days_14d,
                COALESCE(SUM(CASE WHEN created_at >= ? AND created_at < ? THEN 1 ELSE 0 END), 0) AS events_prior
            FROM user_activity_events
            WHERE user_id IN ({placeholders}) AND created_at >= ?
            GROUP BY user_id
            """,
            [d14_ago, d14_ago, d30_ago, d14_ago, *clean_ids, d30_ago],
        )
        stats_map = {int(r[0]): (int(r[1] or 0), int(r[2] or 0), int(r[3] or 0)) for r in c.fetchall()}

        out: Dict[int, Dict[str, Any]] = {}
        for uid in clean_ids:
            ev14, days14, ev_prior = stats_map.get(uid, (0, 0, 0))
            out[uid] = _build_activity_classification(ev14, days14, ev_prior, pro_map.get(uid, False))
        return out
    finally:
        if should_close and conn:
            conn.close()


def classify_user_activity(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Computes an explainable activity classification for a single user.
    Categories: Highly Active, Active, Occasionally Active, At Risk, Inactive.
    """
    return classify_users_activity_batch([int(user_id)], conn=conn).get(
        int(user_id),
        _build_activity_classification(0, 0, 0, False),
    )


def get_real_activity_analytics() -> Dict[str, Any]:
    """Calculates DAU, WAU, MAU, and user classifications in O(1) constant SQL GROUP BY queries."""
    now_dt = datetime.utcnow()
    d1_ago = (now_dt - timedelta(days=1)).isoformat()
    d7_ago = (now_dt - timedelta(days=7)).isoformat()
    d14_ago = (now_dt - timedelta(days=14)).isoformat()
    d30_ago = (now_dt - timedelta(days=30)).isoformat()
    today_start = now_dt.strftime("%Y-%m-%d")

    with _get_connection() as conn:
        c = conn.cursor()

        c.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0) AS new_today,
                COALESCE(SUM(CASE WHEN last_active_at >= ? THEN 1 ELSE 0 END), 0) AS u_d1,
                COALESCE(SUM(CASE WHEN last_active_at >= ? THEN 1 ELSE 0 END), 0) AS u_d7,
                COALESCE(SUM(CASE WHEN last_active_at >= ? THEN 1 ELSE 0 END), 0) AS u_d30
            FROM telegram_users
            """,
            (today_start, d1_ago, d7_ago, d30_ago),
        )
        u_row = c.fetchone()
        total_users = int(u_row[0] or 0)
        new_users_today = int(u_row[1] or 0)

        # Single combined active-users scan across events, sessions, and telegram_users
        c.execute(
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
            """,
            (d1_ago, d7_ago, d30_ago, d30_ago, d30_ago, d30_ago),
        )
        d_row = c.fetchone()
        dau = int((d_row[0] if d_row else 0) or u_row[2] or 0)
        wau = int((d_row[1] if d_row else 0) or u_row[3] or 0)
        mau = int((d_row[2] if d_row else 0) or u_row[4] or 0)

        engagement_ratio = round((dau / mau * 100), 1) if mau > 0 else 0.0

        c.execute(
            """
            SELECT event_name, COUNT(*) as cnt
            FROM user_activity_events
            GROUP BY event_name
            ORDER BY cnt DESC LIMIT 8
            """
        )
        feature_breakdown = [{"event": row["event_name"], "count": row["cnt"]} for row in c.fetchall()]

        # O(1) query activity classification bucket summary across all users via GROUP BY
        c.execute(
            """
            SELECT
                SUM(CASE WHEN days_14 >= 7 OR ev_14 >= 25 THEN 1 ELSE 0 END) AS highly_active,
                SUM(CASE WHEN NOT (days_14 >= 7 OR ev_14 >= 25) AND (days_14 >= 3 OR ev_14 >= 8) THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN NOT (days_14 >= 3 OR ev_14 >= 8) AND (days_14 >= 1 OR ev_14 >= 1) THEN 1 ELSE 0 END) AS occasional,
                SUM(CASE WHEN days_14 = 0 AND ev_14 = 0 AND ev_prior > 0 THEN 1 ELSE 0 END) AS at_risk,
                SUM(CASE WHEN days_14 = 0 AND ev_14 = 0 AND ev_prior = 0 THEN 1 ELSE 0 END) AS inactive
            FROM (
                SELECT
                    u.user_id,
                    COALESCE(SUM(CASE WHEN e.created_at >= ? THEN 1 ELSE 0 END), 0) AS ev_14,
                    COUNT(DISTINCT CASE WHEN e.created_at >= ? THEN substr(e.created_at, 1, 10) END) AS days_14,
                    COALESCE(SUM(CASE WHEN e.created_at >= ? AND e.created_at < ? THEN 1 ELSE 0 END), 0) AS ev_prior
                FROM telegram_users u
                LEFT JOIN user_activity_events e ON u.user_id = e.user_id AND e.created_at >= ?
                GROUP BY u.user_id
            )
            """,
            (d14_ago, d14_ago, d30_ago, d14_ago, d30_ago),
        )
        cls_row = c.fetchone()
        class_counts = {
            "Highly Active": int((cls_row[0] if cls_row else 0) or 0),
            "Active": int((cls_row[1] if cls_row else 0) or 0),
            "Occasionally Active": int((cls_row[2] if cls_row else 0) or 0),
            "At Risk": int((cls_row[3] if cls_row else 0) or 0),
            "Inactive": int((cls_row[4] if cls_row else 0) or 0),
        }

    return {
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "total_users": total_users,
        "new_users_today": new_users_today,
        "engagement_ratio_pct": engagement_ratio,
        "classification_summary": class_counts,
        "feature_breakdown": feature_breakdown,
        "feature_distribution": {item["event"]: item["count"] for item in feature_breakdown},
    }


def build_retention_query_stmt() -> tuple[str, list]:
    """SQLite & Turso compatible single SQL cohort retention query (avoids full table loads)."""
    sql = """
    SELECT
        reg_date,
        COUNT(*) AS users_count,
        COALESCE(SUM(CASE WHEN EXISTS (
            SELECT 1 FROM user_activity_events e
            WHERE e.user_id = u_base.user_id
              AND substr(e.created_at, 1, 10) = date(u_base.reg_date, '+1 day')
        ) THEN 1 ELSE 0 END), 0) AS d1_retained,
        COALESCE(SUM(CASE WHEN EXISTS (
            SELECT 1 FROM user_activity_events e
            WHERE e.user_id = u_base.user_id
              AND substr(e.created_at, 1, 10) = date(u_base.reg_date, '+7 day')
        ) THEN 1 ELSE 0 END), 0) AS d7_retained,
        COALESCE(SUM(CASE WHEN EXISTS (
            SELECT 1 FROM user_activity_events e
            WHERE e.user_id = u_base.user_id
              AND substr(e.created_at, 1, 10) = date(u_base.reg_date, '+30 day')
        ) THEN 1 ELSE 0 END), 0) AS d30_retained
    FROM (
        SELECT user_id, substr(created_at, 1, 10) AS reg_date
        FROM telegram_users
        WHERE created_at IS NOT NULL AND length(created_at) >= 10
    ) u_base
    GROUP BY reg_date
    ORDER BY reg_date DESC
    LIMIT 10
    """.strip()
    return (sql, [])


def parse_retention_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = []
    for r in rows:
        count = int(r.get("users_count") or 0)
        d1 = int(r.get("d1_retained") or 0)
        d7 = int(r.get("d7_retained") or 0)
        d30 = int(r.get("d30_retained") or 0)
        summary.append({
            "cohort_date": r["reg_date"],
            "users_count": count,
            "d1_retained": d1,
            "d1_pct": round(d1 / count * 100, 1) if count else 0.0,
            "d7_retained": d7,
            "d7_pct": round(d7 / count * 100, 1) if count else 0.0,
            "d30_retained": d30,
            "d30_pct": round(d30 / count * 100, 1) if count else 0.0,
        })
    total_cohort_users = sum(item["users_count"] for item in summary)
    d1_pct = round(sum(item["d1_retained"] for item in summary) / total_cohort_users * 100, 1) if total_cohort_users else 0.0
    d7_pct = round(sum(item["d7_retained"] for item in summary) / total_cohort_users * 100, 1) if total_cohort_users else 0.0
    d30_pct = round(sum(item["d30_retained"] for item in summary) / total_cohort_users * 100, 1) if total_cohort_users else 0.0
    return {"d1_pct": d1_pct, "d7_pct": d7_pct, "d30_pct": d30_pct, "cohorts": summary}


def get_retention_analytics() -> Dict[str, Any]:
    """Calculates D1, D7, and D30 user retention metrics via single SQL GROUP BY cohort query."""
    sql, params = build_retention_query_stmt()
    with _get_connection() as conn:
        from src.db_adapter import fetch_batch_dicts
        rows = fetch_batch_dicts(conn, [(sql, params)])[0]
    return parse_retention_rows(rows)
