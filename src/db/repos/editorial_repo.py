"""Editorial review queue and Amaliy practical modules persistence repository."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.db.repos.base import BaseRepo
from src.db.provenance_classifier import list_editorial_queue


class EditorialRepo(BaseRepo):
    """Repository for editorial queue queries and completed practical learning modules."""

    def get_completed_modules(self, user_id: int) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT module_id FROM user_completed_modules WHERE user_id = ?", (user_id,))
            return [r[0] for r in c.fetchall()]

    def is_module_completed(self, user_id: int, module_id: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT 1 FROM user_completed_modules WHERE user_id = ? AND module_id = ?",
                (user_id, module_id),
            )
            return c.fetchone() is not None

    def toggle_completed_module(self, user_id: int, module_id: str) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT 1 FROM user_completed_modules WHERE user_id = ? AND module_id = ?",
                (user_id, module_id),
            )
            if c.fetchone():
                c.execute(
                    "DELETE FROM user_completed_modules WHERE user_id = ? AND module_id = ?",
                    (user_id, module_id),
                )
                conn.commit()
                return False
            c.execute(
                "INSERT INTO user_completed_modules (user_id, module_id, completed_at) VALUES (?, ?, ?)",
                (user_id, module_id, now_ts),
            )
            conn.commit()
            return True

    def list_editorial_queue(
        self,
        status: str = "PENDING_EDITORIAL_REVIEW",
        limit: int = 50,
        offset: int = 0,
        issue_flag: Optional[str] = None,
        q: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegates editorial review queue reads cleanly using batched Turso queries."""
        with self._get_connection() as conn:
            return list_editorial_queue(
                conn,
                status=status,
                limit=limit,
                offset=offset,
                issue_flag=issue_flag,
                q=q,
                source_type=source_type,
            )
