"""SM-2 Spaced Repetition repository (`user_question_srs`) with DB-backed undo/recalibration state."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple
from src.db.repos.base import BaseRepo
from src.db.sm2_engine import (
    build_srs_upsert_stmt,
    classify_srs_mastery,
    compute_next_sm2_state,
    serialize_srs_prev_state,
)


class SrsRepo(BaseRepo):
    """Repository managing SM-2 spaced repetition state, due queues, and atomic recalibrations."""

    @staticmethod
    def build_aggregate_stmt(user_id: int, now_iso: Optional[str] = None) -> Tuple[str, List[Any]]:
        now_ts = now_iso or datetime.utcnow().isoformat()
        end_of_day_ts = f"{now_ts[:10]}T23:59:59.999999"
        sql = """
        SELECT
            COUNT(*) AS tracked_count,
            COALESCE(SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END), 0) AS due_now_count,
            COALESCE(SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END), 0) AS due_today_count,
            COALESCE(SUM(CASE WHEN repetitions <= 0 OR (repetitions = 1 AND lapses > 1) THEN 1 ELSE 0 END), 0) AS learning_count,
            COALESCE(SUM(CASE WHEN repetitions >= 3 AND interval_days >= 21 AND ease_factor >= 2.0 THEN 1 ELSE 0 END), 0) AS mastered_count,
            COALESCE(AVG(ease_factor), 2.5) AS avg_ease_factor
        FROM user_question_srs
        WHERE user_id = ?
        """
        return (sql.strip(), [now_ts, end_of_day_ts, user_id])

    @staticmethod
    def parse_aggregate_row(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        r = row or {}
        tracked = int(r.get("tracked_count") or 0)
        due_now = int(r.get("due_now_count") or 0)
        due_today = int(r.get("due_today_count") or 0)
        learning = int(r.get("learning_count") or 0)
        mastered = int(r.get("mastered_count") or 0)
        reviewing = max(0, tracked - learning - mastered)
        avg_ef = round(float(r.get("avg_ease_factor") or 2.5), 2) if tracked > 0 else 2.5
        retention = round(((tracked - min(tracked, due_now)) / tracked) * 100.0, 1) if tracked > 0 else 0.0
        return {
            "tracked_count": tracked,
            "due_now_count": due_now,
            "due_today_count": due_today,
            "learning_count": learning,
            "reviewing_count": reviewing,
            "mastered_count": mastered,
            "avg_ease_factor": avg_ef,
            "retention_rate": retention,
        }

    def query_srs_aggregate(self, conn: Any, user_id: int, now_iso: Optional[str] = None) -> Dict[str, Any]:
        """Executes single-query SM-2 aggregate summary on an open connection."""
        sql, params = self.build_aggregate_stmt(user_id, now_iso=now_iso)
        c = conn.cursor()
        c.execute(sql, tuple(params))
        row = c.fetchone()
        return self.parse_aggregate_row(dict(row) if row else {})

    def record_srs_review(
        self,
        user_id: int,
        canonical_id: str,
        quality: int,
        now_dt: Optional[datetime] = None,
        recalibrate: bool = False,
    ) -> Dict[str, Any]:
        """
        Records a direct SM-2 recall rating (0..5) and updates user_mistakes atomically.
        When recalibrate=True, restores pre-answer state from persisted DB column prev_state_json
        so stateless workers never double-increment repetitions.
        """
        ts_dt = now_dt or datetime.utcnow()
        now_ts = ts_dt.isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT ease_factor, interval_days, repetitions, lapses,
                       last_quality, last_reviewed_at, next_review_at, prev_state_json
                FROM user_question_srs
                WHERE user_id = ? AND canonical_id = ?
                """,
                (user_id, canonical_id),
            )
            row = c.fetchone()
            row_dict = dict(row) if row else None

            if recalibrate and row_dict and row_dict.get("prev_state_json") is not None:
                raw_prev = row_dict["prev_state_json"]
                try:
                    prev = json.loads(raw_prev)
                except Exception:
                    prev = row_dict
                preserved_prev_json = str(raw_prev)
            else:
                prev = row_dict
                preserved_prev_json = serialize_srs_prev_state(prev)

            next_srs = compute_next_sm2_state(prev, quality=quality, now=ts_dt)
            batch_stmts: List[Any] = [
                build_srs_upsert_stmt(user_id, canonical_id, next_srs, prev_state_json=preserved_prev_json)
            ]
            if next_srs["last_quality"] >= 4:
                batch_stmts.append((
                    "UPDATE user_mistakes SET is_resolved = 1 WHERE user_id = ? AND canonical_id = ?",
                    [user_id, canonical_id],
                ))
            elif next_srs["last_quality"] < 3:
                batch_stmts.append((
                    """
                    INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, last_mistake_at, is_resolved)
                    VALUES (?, ?, 1, ?, 0)
                    ON CONFLICT(user_id, canonical_id) DO UPDATE SET
                        mistake_count = mistake_count + 1,
                        last_mistake_at = excluded.last_mistake_at,
                        is_resolved = 0
                    """.strip(),
                    [user_id, canonical_id, now_ts],
                ))
            self._batch_write(conn, batch_stmts)
            return next_srs

    def get_srs_queue_summary(
        self,
        user_id: int,
        now_iso: Optional[str] = None,
        total_bank_questions: int = 1327,
        limit: int = 30,
    ) -> Dict[str, Any]:
        """Fetches SM-2 aggregate summary and urgent due-queue items in 1 batched round-trip."""
        now_ts = now_iso or datetime.utcnow().isoformat()
        agg_stmt = self.build_aggregate_stmt(user_id, now_iso=now_ts)
        queue_stmt = (
            """
            SELECT canonical_id, ease_factor, interval_days, repetitions, lapses,
                   last_quality, last_reviewed_at, next_review_at
            FROM user_question_srs
            WHERE user_id = ?
            ORDER BY
                CASE WHEN next_review_at <= ? THEN 0 ELSE 1 END ASC,
                next_review_at ASC,
                ease_factor ASC,
                lapses DESC
            LIMIT ?
            """.strip(),
            [user_id, now_ts, max(1, int(limit))],
        )
        with self._get_connection() as conn:
            res_sets = self._batch_read(conn, [agg_stmt, queue_stmt])

        agg = self.parse_aggregate_row(res_sets[0][0] if res_sets[0] else {})
        agg["total_bank_questions"] = int(total_bank_questions)

        items: List[Dict[str, Any]] = []
        due_ids: List[str] = []
        for d in res_sets[1]:
            is_due = str(d["next_review_at"]) <= now_ts
            item = {
                **d,
                "is_due": is_due,
                "ease_factor": round(float(d.get("ease_factor") or 2.5), 2),
                "interval_days": int(d.get("interval_days") or 0),
                "repetitions": int(d.get("repetitions") or 0),
                "lapses": int(d.get("lapses") or 0),
                "mastery_level": classify_srs_mastery(
                    int(d.get("repetitions") or 0),
                    int(d.get("interval_days") or 0),
                    round(float(d.get("ease_factor") or 2.5), 2),
                    int(d.get("lapses") or 0),
                ),
            }
            items.append(item)
            if is_due:
                due_ids.append(d["canonical_id"])

        return {"summary": agg, "due_question_ids": due_ids, "items": items}

    def get_question_srs_map(self, user_id: int, canonical_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Returns compact SM-2 retention state keyed by canonical_id."""
        clean_ids = [str(cid) for cid in canonical_ids if cid]
        if not clean_ids:
            return {}
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            ph = ",".join("?" for _ in clean_ids)
            c.execute(
                f"""
                SELECT canonical_id, ease_factor, interval_days, repetitions, lapses, last_quality, next_review_at
                FROM user_question_srs
                WHERE user_id = ? AND canonical_id IN ({ph})
                """,
                tuple([user_id] + clean_ids),
            )
            out: Dict[str, Dict[str, Any]] = {}
            for r in c.fetchall():
                ef = round(float(r["ease_factor"] or 2.5), 2)
                iv = int(r["interval_days"] or 0)
                reps = int(r["repetitions"] or 0)
                lapses = int(r["lapses"] or 0)
                nra = str(r["next_review_at"])
                out[r["canonical_id"]] = {
                    "ease_factor": ef,
                    "interval_days": iv,
                    "repetitions": reps,
                    "lapses": lapses,
                    "last_quality": int(r["last_quality"] or 0),
                    "next_review_at": nra,
                    "is_due": nra <= now_ts,
                    "mastery_level": classify_srs_mastery(reps, iv, ef, lapses),
                }
            return out
