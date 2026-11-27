"""Sessions, answers, Bilet progress, and atomic answer processing repository."""

from datetime import datetime
import json
import secrets
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional, Set
from src.db.repos.base import BaseRepo
from src.db.sm2_engine import (
    build_srs_upsert_stmt,
    classify_srs_mastery,
    compute_next_sm2_state,
    derive_sm2_quality,
    serialize_srs_prev_state,
)
from src.db.tz_utils import tashkent_now, tashkent_today_str, tashkent_yesterday_str


class SessionsRepo(BaseRepo):
    """Repository managing active sessions, answers, Bilet mastery, and atomic answer flows."""

    def create_session(
        self,
        user_id: int,
        session_type: str,
        language: str,
        question_ids: List[str],
        time_limit_seconds: int = 0,
        category_id: Optional[int] = None,
        show_answer: bool = True,
        show_explanation: bool = True,
        preloaded_bookmarks: Optional[Set[str]] = None,
        log_event_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new study/exam session atomically (aborting any prior IN_PROGRESS session),
        optionally recording a telemetry event in the same write batch to stay <= 2 Turso RTs.
        """
        session_id = f"SES-{int(time.time() * 1000)}-{user_id}-{secrets.token_hex(2)}"
        now_ts = datetime.utcnow().isoformat()
        start_t = time.time()
        deadline = (start_t + time_limit_seconds) if time_limit_seconds > 0 else None

        batch_stmts: List[Any] = [
            ("UPDATE user_sessions SET status = 'ABORTED' WHERE user_id = ? AND status = 'IN_PROGRESS'", [user_id]),
            (
                """
                INSERT INTO user_sessions (
                    session_id, user_id, session_type, category_id, language,
                    total_questions, current_index, correct_count, incorrect_count,
                    status, start_time, time_limit_seconds, deadline, question_ids_json,
                    show_answer, show_explanation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 'IN_PROGRESS', ?, ?, ?, ?, ?, ?, ?, ?)
                """.strip(),
                [
                    session_id,
                    user_id,
                    session_type,
                    category_id,
                    language,
                    len(question_ids),
                    start_t,
                    time_limit_seconds,
                    deadline,
                    json.dumps(question_ids),
                    1 if show_answer else 0,
                    1 if show_explanation else 0,
                    now_ts,
                    now_ts,
                ],
            ),
        ]
        if log_event_data is not None:
            batch_stmts.append((
                "INSERT INTO user_activity_events (user_id, event_name, event_data, created_at) VALUES (?, ?, ?, ?)",
                [user_id, "QUIZ_STARTED", json.dumps(log_event_data), now_ts],
            ))

        with self._get_connection() as conn:
            self._batch_write(conn, batch_stmts)
            if preloaded_bookmarks is not None:
                bm_ids = set(preloaded_bookmarks)
            else:
                c = conn.cursor()
                c.execute("SELECT canonical_id FROM user_bookmarks WHERE user_id = ?", (user_id,))
                bm_ids = {r["canonical_id"] for r in c.fetchall()}

        return {
            "session_id": session_id,
            "user_id": user_id,
            "session_type": session_type,
            "category_id": category_id,
            "language": language,
            "total_questions": len(question_ids),
            "current_index": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "status": "IN_PROGRESS",
            "start_time": start_t,
            "time_limit_seconds": time_limit_seconds,
            "deadline": deadline,
            "question_ids": question_ids,
            "show_answer": bool(show_answer),
            "show_explanation": bool(show_explanation),
            "created_at": now_ts,
            "updated_at": now_ts,
            "bookmark_ids": bm_ids,
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM user_sessions WHERE session_id = ?", (session_id,))
            row = c.fetchone()
            if not row:
                return None
            res = dict(row)
            res["question_ids"] = json.loads(res["question_ids_json"])
            res["show_answer"] = bool(res.get("show_answer", 1))
            res["show_explanation"] = bool(res.get("show_explanation", 1))
            return res

    def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT * FROM user_sessions
                WHERE user_id = ? AND status = 'IN_PROGRESS'
                ORDER BY start_time DESC LIMIT 1
                """,
                (user_id,),
            )
            row = c.fetchone()
            if not row:
                return None
            res = dict(row)
            res["question_ids"] = json.loads(res["question_ids_json"])
            res["show_answer"] = bool(res.get("show_answer", 1))
            res["show_explanation"] = bool(res.get("show_explanation", 1))
            return res

    def save_answer(
        self,
        session_id: str,
        canonical_id: str,
        selected_key: str,
        correct_key: str,
        is_correct: bool,
    ) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(
                    """
                    INSERT INTO session_answers (
                        session_id, user_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                    ) VALUES (
                        ?, (SELECT user_id FROM user_sessions WHERE session_id = ? LIMIT 1), ?, ?, ?, ?, ?
                    )
                    """,
                    (session_id, session_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts),
                )
            except sqlite3.IntegrityError:
                return False

            col = "correct_count" if is_correct else "incorrect_count"
            c.execute(f"UPDATE user_sessions SET {col} = {col} + 1, updated_at = ? WHERE session_id = ?", (now_ts, session_id))
            conn.commit()
            return True

    def _compute_streak_transition(
        self,
        user_id: int,
        st_row: Optional[Dict[str, Any]],
        now_utc_ts: str,
    ) -> tuple[Dict[str, Any], tuple[str, List[Any]]]:
        t_now = tashkent_now()
        today_str = tashkent_today_str(t_now)
        yesterday_str = tashkent_yesterday_str(t_now)
        if st_row:
            last_date = st_row.get("last_active_date")
            prev_streak = int(st_row.get("current_streak") or 0)
            goal_q = int(st_row.get("daily_goal_questions") or 20)
            if last_date == today_str:
                new_streak = max(1, prev_streak)
                new_today = int(st_row.get("today_questions_count") or 0) + 1
            elif last_date == yesterday_str:
                new_streak = max(1, prev_streak + 1)
                new_today = 1
            else:
                new_streak = 1
                new_today = 1
            stmt = (
                "UPDATE learning_streak SET current_streak = ?, today_questions_count = ?, last_active_date = ?, updated_at = ? WHERE user_id = ?",
                [new_streak, new_today, today_str, now_utc_ts, user_id],
            )
            return {"current_streak": new_streak, "today_questions_count": new_today, "daily_goal_questions": goal_q}, stmt

        stmt = (
            """
            INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
            VALUES (?, 1, ?, 20, 1, ?)
            """.strip(),
            [user_id, today_str, now_utc_ts],
        )
        return {"current_streak": 1, "today_questions_count": 1, "daily_goal_questions": 20}, stmt

    def _read_answer_prereqs(
        self,
        conn: Any,
        session_id: str,
        user_id: int,
        canonical_id: str,
    ) -> Dict[str, Any]:
        """Executes all 4 pre-read checks in 1 single batched round-trip."""
        batches = self._batch_read(
            conn,
            [
                (
                    "SELECT user_id, session_type, language, status, incorrect_count FROM user_sessions WHERE session_id = ?",
                    [session_id],
                ),
                (
                    """
                    SELECT ease_factor, interval_days, repetitions, lapses,
                           last_quality, last_reviewed_at, next_review_at
                    FROM user_question_srs
                    WHERE user_id = ? AND canonical_id = ?
                    """.strip(),
                    [user_id, canonical_id],
                ),
                (
                    "SELECT is_correct FROM session_answers WHERE session_id = ? AND canonical_id = ?",
                    [session_id, canonical_id],
                ),
                (
                    "SELECT current_streak, today_questions_count, last_active_date, daily_goal_questions FROM learning_streak WHERE user_id = ?",
                    [user_id],
                ),
            ],
        )
        return {
            "session": batches[0][0] if batches[0] else None,
            "prev_srs": batches[1][0] if batches[1] else None,
            "existing_ans": batches[2][0] if batches[2] else None,
            "streak_row": batches[3][0] if batches[3] else None,
        }

    def process_session_answer(
        self,
        session_id: str,
        user_id: int,
        canonical_id: str,
        selected_key: str,
        correct_key: str,
        is_correct: bool,
        session_type: str = "EXAM",
        response_time_ms: Optional[int] = None,
        quality: Optional[int] = None,
        _preloaded: Optional[Dict[str, Any]] = None,
        _conn: Any = None,
    ) -> Dict[str, Any]:
        """
        Atomic answer execution, mistake tracking, Tashkent UTC+5 streak update,
        DB-backed SM-2 undo snapshot persistence, and EXAM termination check in <= 2 RTs.
        """
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()

        def _run_with_conn(conn: Any) -> Dict[str, Any]:
            ctx = _preloaded if _preloaded is not None else self._read_answer_prereqs(conn, session_id, user_id, canonical_id)
            sess_row = ctx["session"]
            prev_srs = ctx["prev_srs"]
            existing_ans = ctx["existing_ans"]
            st_row = ctx["streak_row"]
            eff_type = (sess_row.get("session_type") if sess_row else None) or session_type

            if eff_type == "EXAM" and sess_row and (
                sess_row["status"] in ("FAILED_MISTAKES", "COMPLETED", "TERMINATED")
                or int(sess_row.get("incorrect_count") or 0) >= 3
            ):
                return {
                    "is_new": False,
                    "streak": {"current_streak": 0, "today_questions_count": 0},
                    "is_exam_terminated": True,
                    "srs": None,
                }

            if existing_ans is not None:
                cur_srs = None
                if prev_srs:
                    cur_srs = {
                        **prev_srs,
                        "mastery_level": classify_srs_mastery(
                            int(prev_srs.get("repetitions") or 0),
                            int(prev_srs.get("interval_days") or 0),
                            float(prev_srs.get("ease_factor") or 2.5),
                            int(prev_srs.get("lapses") or 0),
                        ),
                    }
                return {
                    "is_new": False,
                    "streak": {
                        "current_streak": int(st_row["current_streak"]) if st_row else 0,
                        "today_questions_count": int(st_row["today_questions_count"]) if st_row else 0,
                    },
                    "is_exam_terminated": (sess_row["status"] == "FAILED_MISTAKES") if sess_row else False,
                    "srs": cur_srs,
                }

            streak_info, streak_stmt = self._compute_streak_transition(user_id, st_row, now_ts)
            curr_incorrect = int(sess_row.get("incorrect_count") or 0) if sess_row else 0
            new_incorrect = curr_incorrect + (0 if is_correct else 1)
            is_exam_terminated = (eff_type == "EXAM" and new_incorrect >= 3)

            derived_q = derive_sm2_quality(
                is_correct=is_correct,
                session_type=eff_type,
                response_time_ms=response_time_ms,
                previous_lapses=int(prev_srs.get("lapses") or 0) if prev_srs else 0,
                explicit_quality=quality,
            )
            next_srs = compute_next_sm2_state(prev_srs, quality=derived_q, now=now_dt)
            prev_json = serialize_srs_prev_state(prev_srs)

            batch_stmts: List[Any] = [
                (
                    """
                    INSERT INTO session_answers (
                        session_id, user_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """.strip(),
                    [session_id, user_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts],
                )
            ]
            if is_correct:
                batch_stmts.append((
                    "UPDATE user_sessions SET correct_count = correct_count + 1, updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id],
                ))
                batch_stmts.append((
                    "UPDATE user_mistakes SET is_resolved = 1 WHERE user_id = ? AND canonical_id = ?",
                    [user_id, canonical_id],
                ))
            else:
                batch_stmts.append((
                    "UPDATE user_sessions SET incorrect_count = incorrect_count + 1, updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id],
                ))
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

            batch_stmts.append(streak_stmt)
            batch_stmts.append(build_srs_upsert_stmt(user_id, canonical_id, next_srs, prev_state_json=prev_json))
            if is_exam_terminated:
                batch_stmts.append((
                    "UPDATE user_sessions SET status = 'FAILED_MISTAKES', updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id],
                ))

            self._batch_write(conn, batch_stmts)
            return {
                "is_new": True,
                "streak": streak_info,
                "is_exam_terminated": is_exam_terminated,
                "srs": next_srs,
            }

        if _conn is not None:
            return _run_with_conn(_conn)
        with self._get_connection() as conn:
            return _run_with_conn(conn)

    def submit_session_answer_verified(
        self,
        session_id: str,
        user_id: int,
        canonical_id: str,
        selected_key: str,
        answer_checker: Callable[[str, str, str], Any],
        requested_lang: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        quality: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Single-entry verified answer pipeline for API route:
        1) 1 batched read (ownership, session status, SRS state, idempotency, streak)
        2) In-memory answer grading (0 DB RTs on warm cache)
        3) 1 batched write -> strict 2 Turso HTTP round-trips total.
        """
        with self._get_connection() as conn:
            ctx = self._read_answer_prereqs(conn, session_id, user_id, canonical_id)
            sess_row = ctx["session"]
            if not sess_row:
                return {"error": "NOT_FOUND"}
            if int(sess_row["user_id"]) != int(user_id):
                return {"error": "FORBIDDEN"}

            sess_type = sess_row.get("session_type") or "EXAM"
            if sess_type == "EXAM" and (
                sess_row["status"] in ("FAILED_MISTAKES", "COMPLETED", "TERMINATED")
                or int(sess_row.get("incorrect_count") or 0) >= 3
            ):
                return {
                    "early_terminated": True,
                    "session_type": sess_type,
                }

            lang = requested_lang or sess_row.get("language") or "uz_latn"
            feedback = answer_checker(canonical_id, selected_key, lang)
            res = self.process_session_answer(
                session_id=session_id,
                user_id=user_id,
                canonical_id=canonical_id,
                selected_key=selected_key.upper(),
                correct_key=feedback.correct_key,
                is_correct=feedback.is_correct,
                session_type=sess_type,
                response_time_ms=response_time_ms,
                quality=quality,
                _preloaded=ctx,
                _conn=conn,
            )
            return {
                "early_terminated": False,
                "feedback": feedback,
                "result": res,
            }

    def get_session_answers(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT canonical_id, selected_key, correct_key, is_correct, answered_at
                FROM session_answers
                WHERE session_id = ?
                """,
                (session_id,),
            )
            return {
                r["canonical_id"]: {
                    "selected_key": r["selected_key"],
                    "correct_key": r["correct_key"],
                    "is_correct": bool(r["is_correct"]),
                    "answered_at": r["answered_at"],
                }
                for r in c.fetchall()
            }

    def advance_session(self, session_id: str) -> int:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE user_sessions SET current_index = current_index + 1, updated_at = ? WHERE session_id = ?",
                (now_ts, session_id),
            )
            c.execute("SELECT current_index FROM user_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return int(c.fetchone()["current_index"])

    def finish_session(self, session_id: str, status: str = "COMPLETED") -> Optional[Dict[str, Any]]:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_sessions SET status = ?, updated_at = ? WHERE session_id = ?", (status, now_ts, session_id))
            conn.commit()
        return self.get_session(session_id)

    def upsert_ticket_progress(
        self,
        user_id: int,
        ticket_number: int,
        total_questions: int,
        correct_count: int,
        percentage: float,
        passed: bool,
        session_id: str,
    ) -> None:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
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
                """,
                (user_id, ticket_number, total_questions, correct_count, percentage, 1 if passed else 0, session_id, now_ts),
            )
            conn.commit()

    def get_ticket_progress_map(self, user_id: int) -> Dict[int, Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT ticket_number, total_questions, best_correct, best_percentage,
                       attempts_count, is_passed, last_session_id, last_attempted_at
                FROM user_ticket_progress
                WHERE user_id = ?
                """,
                (user_id,),
            )
            return {
                int(r["ticket_number"]): {
                    "ticket_number": int(r["ticket_number"]),
                    "total_questions": int(r["total_questions"]),
                    "best_correct": int(r["best_correct"]),
                    "best_percentage": float(r["best_percentage"]),
                    "attempts_count": int(r["attempts_count"]),
                    "is_passed": bool(r["is_passed"]),
                    "last_session_id": r["last_session_id"],
                    "last_attempted_at": r["last_attempted_at"],
                }
                for r in c.fetchall()
            }

    def get_solved_correct_ids(self, user_id: int) -> Set[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT DISTINCT canonical_id FROM session_answers WHERE user_id = ? AND is_correct = 1",
                (user_id,),
            )
            return {r["canonical_id"] for r in c.fetchall()}

    def get_session_review(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Loads session, answers, and bookmarks atomically in 1 single batched round-trip."""
        with self._get_connection() as conn:
            batches = self._batch_read(
                conn,
                [
                    ("SELECT * FROM user_sessions WHERE session_id = ?", [session_id]),
                    (
                        "SELECT canonical_id, selected_key, correct_key, is_correct, answered_at FROM session_answers WHERE session_id = ?",
                        [session_id],
                    ),
                    ("SELECT canonical_id FROM user_bookmarks WHERE user_id = ?", [user_id]),
                ],
            )
        if not batches[0]:
            return None
        sess = dict(batches[0][0])
        if int(sess.get("user_id") or 0) != int(user_id):
            return {"session": sess, "forbidden": True, "answers": {}, "bookmarks": set()}
        sess["question_ids"] = json.loads(sess["question_ids_json"])
        sess["show_answer"] = bool(sess.get("show_answer", 1))
        sess["show_explanation"] = bool(sess.get("show_explanation", 1))
        answers = {
            r["canonical_id"]: {
                "selected_key": r["selected_key"],
                "correct_key": r["correct_key"],
                "is_correct": bool(r["is_correct"]),
                "answered_at": r["answered_at"],
            }
            for r in batches[1]
        }
        bookmarks = {r["canonical_id"] for r in batches[2]}
        return {"session": sess, "answers": answers, "bookmarks": bookmarks}

    def get_session_finish_bundle(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Loads session and its answers in 1 batched round-trip for /api/session/finish."""
        with self._get_connection() as conn:
            batches = self._batch_read(
                conn,
                [
                    ("SELECT * FROM user_sessions WHERE session_id = ?", [session_id]),
                    (
                        "SELECT canonical_id, selected_key, correct_key, is_correct, answered_at FROM session_answers WHERE session_id = ?",
                        [session_id],
                    ),
                ],
            )
        if not batches[0]:
            return None
        sess = dict(batches[0][0])
        sess["question_ids"] = json.loads(sess["question_ids_json"])
        answers = {
            r["canonical_id"]: {
                "selected_key": r["selected_key"],
                "correct_key": r["correct_key"],
                "is_correct": bool(r["is_correct"]),
                "answered_at": r["answered_at"],
            }
            for r in batches[1]
        }
        return {"session": sess, "answers": answers}
