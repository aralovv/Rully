"""Payments and subscription entitlement repository."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from src.db.repos.base import BaseRepo
from src.db.tz_utils import compute_free_tier_from_counts, evaluate_subscription_row, parse_iso_dt

DEFAULT_SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
    "pro_14": {
        "id": "pro_14",
        "name": "14 kunlik PRO (2 hafta)",
        "duration_days": 14,
        "price_uzs": 14000,
        "price_formatted": "14 000 so‘m",
        "stars_price": 78,
    },
    "pro_30": {
        "id": "pro_30",
        "name": "30 kunlik PRO (1 oy)",
        "duration_days": 30,
        "price_uzs": 25000,
        "price_formatted": "25 000 so‘m",
        "stars_price": 139,
    },
}


class PaymentsRepo(BaseRepo):
    """Repository managing PRO subscription status, free-tier gating, and activations."""

    def get_user_subscription(self, user_id: int) -> Dict[str, Any]:
        """Validates live subscription status and automatically downgrades expired PRO users."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT is_pro, subscription_tier, subscription_expires_at FROM telegram_users WHERE user_id = ?",
                (user_id,),
            )
            row = c.fetchone()
            row_dict = dict(row) if row else None
            sub, expired = evaluate_subscription_row(row_dict)
            if expired:
                c.execute(
                    "UPDATE telegram_users SET is_pro = 0, subscription_tier = 'free' WHERE user_id = ?",
                    (user_id,),
                )
                conn.commit()
            return sub

    def get_user_exam_count(self, user_id: int) -> int:
        """Counts completed exams plus substantially started (>= 3 answers) active EXAM sessions."""
        with self._get_connection() as conn:
            rows = self._batch_read(
                conn,
                [
                    ("SELECT COUNT(*) AS cnt FROM exam_results WHERE user_id = ?", [user_id]),
                    (
                        """
                        SELECT COUNT(*) AS cnt FROM (
                            SELECT us.session_id
                            FROM user_sessions us
                            JOIN session_answers sa ON us.session_id = sa.session_id
                            LEFT JOIN exam_results er ON us.session_id = er.session_id
                            WHERE us.user_id = ? AND us.session_type = 'EXAM' AND er.id IS NULL
                            GROUP BY us.session_id
                            HAVING COUNT(sa.id) >= 3
                        )
                        """.strip(),
                        [user_id],
                    ),
                ],
            )
            finished = int(rows[0][0]["cnt"] or 0) if rows[0] else 0
            unfinished = int(rows[1][0]["cnt"] or 0) if rows[1] else 0
            return finished + unfinished

    def get_user_free_tier_status(
        self,
        user_id: int,
        subscription: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Computes whether a Free-tier user still has of the 2 complimentary EXAM attempts."""
        sub = subscription if subscription is not None else self.get_user_subscription(user_id)
        if sub.get("is_pro"):
            return compute_free_tier_from_counts(sub, 0)
        used = self.get_user_exam_count(user_id)
        return compute_free_tier_from_counts(sub, used)

    def _resolve_plan(self, conn: Any, plan_id: str) -> Dict[str, Any]:
        """Reads live subscription_plans table first, falling back to safe defaults."""
        c = conn.cursor()
        try:
            c.execute("SELECT id, name, duration_days, base_price_uzs FROM subscription_plans WHERE id = ?", (plan_id,))
            row = c.fetchone()
            if row:
                price = int(row["base_price_uzs"] or 0)
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "duration_days": int(row["duration_days"] or 14),
                    "price_uzs": price,
                }
        except Exception:
            pass
        plan_key = "pro_14" if "14" in str(plan_id) else "pro_30"
        return DEFAULT_SUBSCRIPTION_PLANS[plan_key]

    def activate_subscription(self, user_id: int, plan_id: str) -> Dict[str, Any]:
        """Activates or extends a user's PRO subscription atomically using DB plan pricing."""
        now_dt = datetime.utcnow()
        now_str = now_dt.isoformat()

        with self._get_connection() as conn:
            c = conn.cursor()
            plan = self._resolve_plan(conn, plan_id)
            c.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()

            base_dt = now_dt
            if row and row["is_pro"] and row["subscription_expires_at"]:
                current_exp = parse_iso_dt(row["subscription_expires_at"])
                if current_exp and current_exp > now_dt:
                    base_dt = current_exp

            new_expires_str = (base_dt + timedelta(days=int(plan["duration_days"]))).isoformat()
            self._batch_write(
                conn,
                [
                    (
                        """
                        UPDATE telegram_users
                        SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
                        WHERE user_id = ?
                        """,
                        [plan["id"], new_expires_str, user_id],
                    ),
                    (
                        """
                        INSERT INTO user_subscriptions (
                            user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
                        ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                        """,
                        [
                            user_id,
                            plan["id"],
                            plan["name"],
                            int(plan["duration_days"]),
                            int(plan["price_uzs"]),
                            now_str,
                            new_expires_str,
                        ],
                    ),
                ],
            )
        return self.get_user_subscription(user_id)
