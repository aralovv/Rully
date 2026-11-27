"""Exams, mistakes bank, bookmarks, and exam history repository."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from src.db.repos.base import BaseRepo


class ExamsRepo(BaseRepo):
    """Repository handling exam results, unresolved mistakes, and saved bookmarks."""

    # --- Mistakes ---
    def record_mistake(self, user_id: int, canonical_id: str) -> None:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, last_mistake_at, is_resolved)
                VALUES (?, ?, 1, ?, 0)
                ON CONFLICT(user_id, canonical_id) DO UPDATE SET
                    mistake_count = mistake_count + 1,
                    last_mistake_at = excluded.last_mistake_at,
                    is_resolved = 0
                """,
                (user_id, canonical_id, now_ts),
            )
            conn.commit()

    def resolve_mistake(self, user_id: int, canonical_id: str) -> None:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_mistakes SET is_resolved = 1 WHERE user_id = ? AND canonical_id = ?", (user_id, canonical_id))
            conn.commit()

    def get_user_mistakes(self, user_id: int, limit: int = 20) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT canonical_id FROM user_mistakes
                WHERE user_id = ? AND is_resolved = 0
                ORDER BY last_mistake_at DESC LIMIT ?
                """,
                (user_id, limit),
            )
            return [r["canonical_id"] for r in c.fetchall()]

    def get_user_mistakes_count(self, user_id: int) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM user_mistakes WHERE user_id = ? AND is_resolved = 0", (user_id,))
            return int(self._scalar(c.fetchone(), 0, 0))

    # --- Exam Results ---
    def save_exam_result(
        self,
        session_id: str,
        user_id: int,
        total_q: int,
        correct: int,
        incorrect: int,
        pct: float,
        passed: bool,
        time_spent: float,
        category_breakdown: Dict[str, Any],
        unanswered: int = 0,
    ) -> None:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO exam_results (
                    session_id, user_id, total_questions, correct_count, incorrect_count,
                    percentage, passed, time_taken_seconds, category_breakdown_json, created_at,
                    unanswered_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    total_q,
                    correct,
                    incorrect,
                    pct,
                    1 if passed else 0,
                    time_spent,
                    json.dumps(category_breakdown),
                    now_ts,
                    unanswered,
                ),
            )
            conn.commit()

    def finalize_exam_session(
        self,
        session_id: str,
        user_id: int,
        total_q: int,
        correct: int,
        incorrect: int,
        pct: float,
        passed: bool,
        time_spent: float,
        category_breakdown: Dict[str, Any],
        unanswered: int = 0,
        status: str = "COMPLETED",
        record_exam_result: bool = True,
        ticket_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Atomically finishes session, records EXAM result (if official exam), and updates
        BILET ticket progress in a single Turso HTTP write round-trip.
        """
        now_ts = datetime.utcnow().isoformat()
        batch_stmts: List[Any] = []
        if record_exam_result:
            batch_stmts.append((
                """
                INSERT OR REPLACE INTO exam_results (
                    session_id, user_id, total_questions, correct_count, incorrect_count,
                    percentage, passed, time_taken_seconds, category_breakdown_json, created_at,
                    unanswered_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """.strip(),
                [
                    session_id,
                    user_id,
                    total_q,
                    correct,
                    incorrect,
                    pct,
                    1 if passed else 0,
                    time_spent,
                    json.dumps(category_breakdown),
                    now_ts,
                    unanswered,
                ],
            ))
        if ticket_number is not None and int(ticket_number) > 0:
            batch_stmts.append((
                """
                INSERT INTO user_ticket_progress (
                    user_id, ticket_number, total_questions, best_correct,
                    best_percentage, attempts_count, is_passed, last_session_id, last_attempted_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(user_id, ticket_number) DO UPDATE SET
                    total_questions = excluded.total_questions,
                    best_correct = MAX(user_ticket_progress.best_correct, excluded.best_correct),
                    best_percentage = MAX(user_ticket_progress.best_percentage, excluded.best_percentage),
                    attempts_count = user_ticket_progress.attempts_count + 1,
                    is_passed = MAX(user_ticket_progress.is_passed, excluded.is_passed),
                    last_session_id = excluded.last_session_id,
                    last_attempted_at = excluded.last_attempted_at
                """.strip(),
                [user_id, int(ticket_number), total_q, correct, pct, 1 if passed else 0, session_id, now_ts],
            ))
        batch_stmts.append((
            "UPDATE user_sessions SET status = ?, updated_at = ? WHERE session_id = ?",
            [status, now_ts, session_id],
        ))
        with self._get_connection() as conn:
            self._batch_write(conn, batch_stmts)
        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": status,
            "total_questions": total_q,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "percentage": pct,
            "passed": bool(passed),
        }

    def get_user_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM exam_results WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            res = []
            for r in c.fetchall():
                d = dict(r)
                d["category_breakdown"] = json.loads(d["category_breakdown_json"])
                res.append(d)
            return res

    def get_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT session_id, total_questions, correct_count, incorrect_count,
                       percentage, passed, time_taken_seconds, created_at,
                       COALESCE(unanswered_count, 0) AS unanswered_count
                FROM exam_results
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [
                {
                    "session_id": r["session_id"],
                    "total_questions": r["total_questions"],
                    "correct_count": r["correct_count"],
                    "incorrect_count": r["incorrect_count"],
                    "unanswered_count": r["unanswered_count"],
                    "percentage": r["percentage"],
                    "passed": bool(r["passed"]),
                    "time_taken_seconds": r["time_taken_seconds"],
                    "created_at": r["created_at"],
                }
                for r in c.fetchall()
            ]

    # --- Bookmarks ---
    def toggle_bookmark(self, user_id: int, canonical_id: str) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?",
                (user_id, canonical_id),
            )
            if c.fetchone():
                c.execute(
                    "DELETE FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?",
                    (user_id, canonical_id),
                )
                conn.commit()
                return False
            c.execute(
                "INSERT INTO user_bookmarks (user_id, canonical_id, created_at) VALUES (?, ?, ?)",
                (user_id, canonical_id, now_ts),
            )
            conn.commit()
            return True

    def get_user_bookmarks(self, user_id: int) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT canonical_id FROM user_bookmarks WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            )
            return [r[0] for r in c.fetchall()]

    def is_bookmarked(self, user_id: int, canonical_id: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT 1 FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?",
                (user_id, canonical_id),
            )
            return c.fetchone() is not None
