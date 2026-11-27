"""Users repository managing telegram_users identity, preferences, and active checks."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.db.repos.base import BaseRepo
from src.db.tz_utils import evaluate_subscription_row, parse_iso_dt


class UsersRepo(BaseRepo):
    """Data access repository for Telegram user profiles and language preferences."""

    def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        default_lang: str = "uz_latn",
    ) -> Dict[str, Any]:
        """Retrieves or inserts telegram_users row and throttles last_active_at updates (5-min window)."""
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                user_dict = dict(row)
                sub, _ = evaluate_subscription_row(user_dict, now_ts=now_ts, now_dt=now_dt)
                user_dict["subscription"] = {
                    "is_pro": sub["is_pro"],
                    "tier": sub["tier"],
                    "expires_at": sub["expires_at"],
                }

                last_dt = parse_iso_dt(user_dict.get("last_active_at"))
                needs_update = last_dt is None or (now_dt - last_dt).total_seconds() > 300
                if needs_update:
                    c.execute(
                        """
                        UPDATE telegram_users
                        SET username = COALESCE(?, username), first_name = COALESCE(?, first_name),
                            last_name = COALESCE(?, last_name), last_active_at = ?
                        WHERE user_id = ?
                        """,
                        (username, first_name, last_name, now_ts, user_id),
                    )
                    user_dict["last_active_at"] = now_ts
                    conn.commit()
                return user_dict

            c.execute(
                """
                INSERT INTO telegram_users (
                    user_id, username, first_name, last_name, language,
                    is_language_selected, is_pro, subscription_tier, created_at, last_active_at
                )
                VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                """,
                (user_id, username, first_name, last_name, default_lang, now_ts, now_ts),
            )
            conn.commit()
            c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
            user_dict = dict(c.fetchone())
            user_dict["subscription"] = {"is_pro": False, "tier": "free", "expires_at": None}
            return user_dict

    def set_user_language(self, user_id: int, language: str) -> bool:
        """Persists user UI language preference."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE telegram_users SET language = ?, is_language_selected = 1 WHERE user_id = ?",
                (language, user_id),
            )
            conn.commit()
            return c.rowcount > 0

    def has_user_selected_language(self, user_id: int) -> bool:
        """Checks whether user explicitly chose their interface language."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT is_language_selected FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return bool(row["is_language_selected"]) if row else False

    def get_user_language(self, user_id: int) -> str:
        """Returns persisted language code defaulting cleanly to 'uz_latn'."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT language FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return row["language"] if row else "uz_latn"

    def get_all_user_ids(self) -> List[int]:
        """Returns non-blocked Telegram user IDs for operational notifications."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM telegram_users WHERE is_blocked = 0")
            return [r[0] for r in c.fetchall()]
