"""
Analytics & Single-Source-of-Truth Student Metrics Repository ("Ko'rsatkichlar").
Ensures <= 2 Turso HTTP round-trips per boot/analytics call, Asia/Tashkent (UTC+5) streaks,
and zero phantom baselines or practice-drill inflation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from src.db.repos.base import BaseRepo
from src.db.repos.srs_repo import SrsRepo
from src.db.scoring import compute_driver_accuracy, compute_driver_readiness
from src.db.tz_utils import (
    compute_free_tier_from_counts,
    evaluate_subscription_row,
    parse_iso_dt,
    tashkent_now,
    tashkent_today_str,
    tashkent_yesterday_str,
)


class AnalyticsRepo(BaseRepo):
    """Single source of truth for student stats, readiness, analytics, boot bundles, and streaks."""

    def __init__(self, conn_factory=None, db_path: Optional[str] = None, srs_repo: Optional[SrsRepo] = None):
        super().__init__(conn_factory=conn_factory, db_path=db_path)
        self._srs = srs_repo or SrsRepo(conn_factory=conn_factory, db_path=db_path)

    @staticmethod
    def _normalize_streak_row(
        user_id: int,
        row_data: Optional[Dict[str, Any]],
        now_utc_ts: str,
    ) -> Tuple[Dict[str, Any], Optional[Tuple[str, List[Any]]]]:
        """Resolves current streak cleanly in Asia/Tashkent UTC+5 and returns optional SQL sync stmt."""
        t_now = tashkent_now()
        today_str = tashkent_today_str(t_now)
        yesterday_str = tashkent_yesterday_str(t_now)

        if not row_data or row_data.get("last_active_date") is None:
            streak = {
                "current_streak": 0,
                "last_active_date": today_str,
                "daily_goal_questions": 20,
                "today_questions_count": 0,
            }
            return streak, None

        streak_val = int(row_data.get("current_streak") or 0)
        last_date = str(row_data.get("last_active_date") or "")
        goal = int(row_data.get("daily_goal_questions") or 20)
        today_count = int(row_data.get("today_questions_count") or 0)
        write_stmt: Optional[Tuple[str, List[Any]]] = None

        if last_date != today_str:
            if last_date != yesterday_str:
                streak_val = 0
                today_count = 0
                write_stmt = (
                    """
                    UPDATE learning_streak
                    SET current_streak = 0, last_active_date = ?, today_questions_count = 0, updated_at = ?
                    WHERE user_id = ?
                    """.strip(),
                    [today_str, now_utc_ts, user_id],
                )
            else:
                # Active yesterday: preserve last_active_date = yesterday_str until user answers today
                today_count = 0

        return {
            "current_streak": streak_val,
            "last_active_date": last_date if (last_date == yesterday_str) else today_str,
            "daily_goal_questions": goal,
            "today_questions_count": today_count,
        }, write_stmt

    @staticmethod
    def _build_metrics_queries(user_id: int, today_str: str) -> List[Tuple[str, List[Any]]]:
        """Builds core single-batch SQL statements (answer aggregates + scalar counts)."""
        ans_sql = """
        SELECT
            COUNT(sa.id) AS total_ans,
            COALESCE(SUM(sa.is_correct), 0) AS correct_ans,
            COUNT(DISTINCT sa.canonical_id) AS unique_qs,
            COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct,
            COUNT(DISTINCT cq.category_id) AS categories_tested,
            COALESCE(SUM(CASE WHEN COALESCE(us.session_type, '') != 'MISTAKES' THEN 1 ELSE 0 END), 0) AS non_mistake_ans,
            COALESCE(SUM(CASE WHEN COALESCE(us.session_type, '') != 'MISTAKES' AND sa.is_correct = 1 THEN 1 ELSE 0 END), 0) AS non_mistake_correct
        FROM session_answers sa
        LEFT JOIN user_sessions us ON sa.session_id = us.session_id
        LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
        WHERE sa.user_id = ?
        """.strip()

        scalar_sql = """
        SELECT
          (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
          (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
          (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS unresolved_mistakes,
          (SELECT COALESCE(SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS resolved_mistakes,
          (SELECT COUNT(*) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_count,
          (SELECT COALESCE(SUM(passed), 0) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_passed,
          (SELECT COALESCE(AVG(time_taken_seconds), 0) FROM (SELECT time_taken_seconds FROM exam_results WHERE user_id = ? AND time_taken_seconds > 0 ORDER BY id DESC LIMIT 5)) AS recent_avg_exam_time,
          (SELECT COUNT(*) FROM (SELECT sa.is_correct FROM session_answers sa LEFT JOIN user_sessions us ON sa.session_id = us.session_id WHERE sa.user_id = ? AND COALESCE(us.session_type, '') != 'MISTAKES' ORDER BY sa.id DESC LIMIT 40)) AS recent_ans_total,
          (SELECT COALESCE(SUM(is_correct), 0) FROM (SELECT sa.is_correct FROM session_answers sa LEFT JOIN user_sessions us ON sa.session_id = us.session_id WHERE sa.user_id = ? AND COALESCE(us.session_type, '') != 'MISTAKES' ORDER BY sa.id DESC LIMIT 40)) AS recent_ans_correct,
          (SELECT COUNT(*) FROM user_sessions WHERE user_id = ? AND session_type = 'EXAM' AND status = 'IN_PROGRESS') AS active_in_progress_exams,
          (SELECT COUNT(*) FROM user_bookmarks WHERE user_id = ?) AS bookmarks_count,
          (SELECT COUNT(*) FROM user_completed_modules WHERE user_id = ?) AS completed_modules,
          (SELECT COUNT(*) FROM user_ticket_progress WHERE user_id = ? AND is_passed = 1) AS passed_tickets,
          (SELECT COALESCE(MAX(request_count), 0) FROM ai_usage_limits WHERE user_id = ? AND usage_date = ?) AS ai_usage_today
        """.strip()
        scalar_params = [user_id] * 14 + [today_str]
        return [(ans_sql, [user_id]), (scalar_sql, scalar_params)]

    @staticmethod
    def _assemble_stats_payload(
        ans_row: Dict[str, Any],
        scalar_row: Dict[str, Any],
        srs_agg: Dict[str, Any],
        streak_val: int,
        engine_total_questions: int = 1327,
    ) -> Dict[str, Any]:
        """Computes unified honest student metrics without practice-drill inflation or phantom baselines."""
        total_exams = int(scalar_row.get("total_exams") or 0)
        passed_exams = int(scalar_row.get("passed_exams") or 0)
        mistakes_cnt = int(scalar_row.get("unresolved_mistakes") or 0)
        resolved_cnt = int(scalar_row.get("resolved_mistakes") or 0)

        total_ans = int(ans_row.get("total_ans") or 0)
        correct_ans = int(ans_row.get("correct_ans") or 0)
        non_mistake_ans = int(ans_row.get("non_mistake_ans") or 0)
        non_mistake_corr = int(ans_row.get("non_mistake_correct") or 0)
        unique_qs = int(ans_row.get("unique_qs") or 0)
        unique_correct = int(ans_row.get("unique_correct") or 0)
        categories_tested = int(ans_row.get("categories_tested") or 0)

        # Exclude upfront-reveal MISTAKES retries from accuracy if user has regular attempts
        eff_total = non_mistake_ans if non_mistake_ans > 0 else total_ans
        eff_correct = non_mistake_corr if non_mistake_ans > 0 else correct_ans

        recent_exams_count = int(scalar_row.get("recent_exams_count") or 0)
        recent_exams_passed = int(scalar_row.get("recent_exams_passed") or 0)
        recent_pass_rate = round(recent_exams_passed / recent_exams_count * 100.0, 1) if recent_exams_count > 0 else None
        avg_exam_time = float(scalar_row.get("recent_avg_exam_time") or 0.0)
        recent_ans_total = int(scalar_row.get("recent_ans_total") or 0)
        recent_ans_correct = int(scalar_row.get("recent_ans_correct") or 0)
        if recent_ans_total == 0 and total_ans > 0:
            recent_ans_total = eff_total
            recent_ans_correct = eff_correct

        pass_rate = round((passed_exams / total_exams * 100.0), 1) if total_exams > 0 else 0.0
        accuracy_info = compute_driver_accuracy(
            total_answered=eff_total,
            correct_answers=eff_correct,
            unique_questions=unique_qs,
            unique_correct=unique_correct,
            recent_total=recent_ans_total,
            recent_correct=recent_ans_correct,
            categories_tested=categories_tested,
            unresolved_mistakes=mistakes_cnt,
            return_details=True,
            srs_mastered=srs_agg["mastered_count"],
            srs_due=srs_agg["due_now_count"],
            srs_tracked=srs_agg["tracked_count"],
        )
        accuracy = accuracy_info["accuracy"]

        readiness_info = compute_driver_readiness(
            total_exams=total_exams,
            passed_exams=passed_exams,
            pass_rate=pass_rate,
            total_answered=eff_total,
            accuracy=accuracy,
            unique_questions=unique_qs,
            unresolved_mistakes=mistakes_cnt,
            categories_tested=categories_tested,
            resolved_mistakes=resolved_cnt,
            current_streak=streak_val,
            avg_exam_time_seconds=avg_exam_time,
            recent_pass_rate=recent_pass_rate,
            return_details=True,
            srs_mastered=srs_agg["mastered_count"],
            srs_due=srs_agg["due_now_count"],
            srs_tracked=srs_agg["tracked_count"],
        )

        bank_total = max(1, int(engine_total_questions or 1327))
        catalog_coverage_pct = round(min(100.0, (unique_qs / bank_total) * 100.0), 1)

        return {
            "total_exams": total_exams,
            "passed_exams": passed_exams,
            "pass_rate": pass_rate,
            "total_questions_answered": total_ans,
            "correct_answers": correct_ans,
            "accuracy": accuracy,
            "accuracy_details": accuracy_info,
            "unresolved_mistakes": mistakes_cnt,
            "resolved_mistakes": resolved_cnt,
            "unique_questions_tested": unique_qs,
            "catalog_coverage_pct": catalog_coverage_pct,
            "total_bank_questions": bank_total,
            "categories_tested": categories_tested,
            "topic_count_total": 41,
            "streak": streak_val,
            "avg_exam_time_seconds": round(avg_exam_time, 1),
            "readiness_score": readiness_info["readiness_score"],
            "readiness_grade": readiness_info["grade"],
            "readiness_pillars": readiness_info["pillars"],
            "srs_summary": srs_agg,
        }

    def get_user_stats_on_conn(self, conn: Any, user_id: int, engine_total_questions: int = 1327) -> Dict[str, Any]:
        """Fetches unified student stats and synchronized Tashkent UTC+5 streak on an open connection (1-2 RTs)."""
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()
        today_str = tashkent_today_str()
        metrics_stmts = self._build_metrics_queries(user_id, today_str)
        stmts: List[Tuple[str, List[Any]]] = [
            ("SELECT current_streak, last_active_date, daily_goal_questions, today_questions_count FROM learning_streak WHERE user_id = ?", [user_id]),
            *metrics_stmts,
            self._srs.build_aggregate_stmt(user_id, now_iso=now_ts),
        ]
        batches = self._batch_read(conn, stmts)
        streak_row = batches[0][0] if batches[0] else None
        streak_info, sync_stmt = self._normalize_streak_row(user_id, streak_row, now_ts)
        if sync_stmt:
            self._batch_write(conn, [sync_stmt])

        ans_row = batches[1][0] if batches[1] else {}
        scalar_row = batches[2][0] if batches[2] else {}
        srs_agg = self._srs.parse_aggregate_row(batches[3][0] if batches[3] else {})
        return self._assemble_stats_payload(
            ans_row,
            scalar_row,
            srs_agg,
            streak_val=streak_info["current_streak"],
            engine_total_questions=engine_total_questions,
        )

    def get_user_stats(self, user_id: int, engine_total_questions: int = 1327) -> Dict[str, Any]:
        """Fetches unified student stats and synchronized Tashkent UTC+5 streak in 1-2 RTs."""
        with self._get_connection() as conn:
            return self.get_user_stats_on_conn(conn, user_id, engine_total_questions=engine_total_questions)

    @staticmethod
    def _assemble_analytics_payload(
        categories: List[Dict[str, Any]],
        cat_perf_rows: List[Dict[str, Any]],
        cat_mistakes_rows: List[Dict[str, Any]],
        scalar_row: Dict[str, Any],
        srs_agg: Dict[str, Any],
        streak_val: int,
        engine_total_questions: int = 1327,
    ) -> Dict[str, Any]:
        cat_perf = {
            int(r["category_id"]): {
                "total_attempts": int(r["total_attempts"] or 0),
                "correct_attempts": int(r["correct_attempts"] or 0),
                "unique_answered": int(r["unique_answered"] or 0),
                "unique_correct": int(r["unique_correct"] or 0),
            }
            for r in cat_perf_rows
        }
        cat_mistakes = {int(r["category_id"]): int(r["active_mistakes"] or 0) for r in cat_mistakes_rows}

        category_mastery = []
        total_unique_correct = 0
        total_unique_answered = 0
        for cat in categories:
            cid = int(cat["category_id"])
            total_q = int(cat.get("question_count") or 0)
            perf = cat_perf.get(cid, {"total_attempts": 0, "correct_attempts": 0, "unique_answered": 0, "unique_correct": 0})
            mistakes_here = cat_mistakes.get(cid, 0)
            attempts = perf["total_attempts"]
            correct_att = perf["correct_attempts"]
            uniq_ans = perf["unique_answered"]
            uniq_corr = perf["unique_correct"]
            total_unique_correct += uniq_corr
            total_unique_answered += uniq_ans

            acc_pct = round((correct_att / attempts) * 100.0, 1) if attempts > 0 else None
            mastery_pct = round((uniq_corr / total_q) * 100.0, 1) if total_q > 0 else 0.0
            category_mastery.append({
                "category_id": cid,
                "name": cat["name"],
                "total_questions": total_q,
                "attempts": attempts,
                "correct": correct_att,
                "unique_answered": uniq_ans,
                "unique_correct": uniq_corr,
                "accuracy_pct": acc_pct,
                "mastery_pct": min(100.0, mastery_pct),
                "unresolved_mistakes": mistakes_here,
            })

        attempted_cats = [x for x in category_mastery if x["attempts"] > 0]
        weak_categories = sorted(
            [x for x in attempted_cats if (x["accuracy_pct"] is not None and x["accuracy_pct"] < 80.0) or x["unresolved_mistakes"] > 0],
            key=lambda x: ((x["accuracy_pct"] if x["accuracy_pct"] is not None else 0.0), -x["unresolved_mistakes"]),
        )[:5]
        strong_categories = sorted(
            [x for x in attempted_cats if x["accuracy_pct"] is not None and x["accuracy_pct"] >= 80.0],
            key=lambda x: (-x["accuracy_pct"], -x["unique_correct"]),
        )[:5]

        total_exams = int(scalar_row.get("total_exams") or 0)
        passed_exams = int(scalar_row.get("passed_exams") or 0)
        active_mistakes = int(scalar_row.get("unresolved_mistakes") or 0)
        resolved_mistakes = int(scalar_row.get("resolved_mistakes") or 0)
        completed_modules = int(scalar_row.get("completed_modules") or 0)
        passed_tickets = int(scalar_row.get("passed_tickets") or 0)
        srs_due_now = int(srs_agg["due_now_count"])
        srs_mastered = int(srs_agg["mastered_count"])

        if total_unique_answered < 10 and srs_due_now < 5:
            recommendation = {"kind": "adaptive_starter", "target_type": "ADAPTIVE", "target_id": None, "metric": total_unique_answered}
        elif srs_due_now >= 5:
            recommendation = {"kind": "srs_review", "target_type": "SRS", "target_id": None, "metric": srs_due_now}
        elif active_mistakes >= 5:
            recommendation = {"kind": "mistake_drill", "target_type": "MISTAKES", "target_id": None, "metric": active_mistakes}
        elif srs_due_now >= 1:
            recommendation = {"kind": "srs_review", "target_type": "SRS", "target_id": None, "metric": srs_due_now}
        elif weak_categories:
            w = weak_categories[0]
            recommendation = {
                "kind": "weak_topic",
                "target_type": "CATEGORY",
                "target_id": w["category_id"],
                "topic_name": w["name"],
                "metric": w["accuracy_pct"] if w["accuracy_pct"] is not None else 0.0,
            }
        elif total_exams == 0 or passed_exams == 0:
            recommendation = {"kind": "official_exam", "target_type": "EXAM", "target_id": None, "metric": total_exams}
        else:
            recommendation = {
                "kind": "adaptive_mastery",
                "target_type": "ADAPTIVE",
                "target_id": None,
                "metric": round((total_unique_correct / max(1, engine_total_questions)) * 100.0, 1),
            }

        milestones = [
            {"id": "first_steps", "unlocked": total_unique_answered >= 10, "progress": min(10, total_unique_answered), "target": 10},
            {"id": "streak_3", "unlocked": streak_val >= 3, "progress": min(3, streak_val), "target": 3},
            {"id": "exam_passer", "unlocked": passed_exams >= 1, "progress": min(1, passed_exams), "target": 1},
            {"id": "mistake_slayer", "unlocked": resolved_mistakes >= 5, "progress": min(5, resolved_mistakes), "target": 5},
            {"id": "ticket_finisher", "unlocked": passed_tickets >= 5, "progress": min(5, passed_tickets), "target": 5},
            {"id": "practical_pro", "unlocked": completed_modules >= 5, "progress": min(5, completed_modules), "target": 5},
            {"id": "memory_master", "unlocked": srs_mastered >= 25, "progress": min(25, srs_mastered), "target": 25},
        ]

        return {
            "overall_coverage_pct": round((total_unique_answered / max(1, engine_total_questions)) * 100.0, 1),
            "overall_mastery_pct": round((total_unique_correct / max(1, engine_total_questions)) * 100.0, 1),
            "unique_answered": total_unique_answered,
            "unique_correct": total_unique_correct,
            "total_bank_questions": engine_total_questions,
            "topic_count_total": len(categories) or 41,
            "passed_tickets": passed_tickets,
            "completed_modules": completed_modules,
            "srs_summary": srs_agg,
            "category_mastery": category_mastery,
            "weak_categories": weak_categories,
            "strong_categories": strong_categories,
            "recommendation": recommendation,
            "milestones": milestones,
        }

    def get_learning_analytics(
        self,
        user_id: int,
        categories: List[Dict[str, Any]],
        engine_total_questions: int = 1327,
    ) -> Dict[str, Any]:
        """Computes per-category mastery, SM-2 summary, weak/strong rankings, and recommendation in 1 RT."""
        now_ts = datetime.utcnow().isoformat()
        stmts = [
            (
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id,
                       COUNT(sa.id) AS total_attempts,
                       COALESCE(SUM(sa.is_correct), 0) AS correct_attempts,
                       COUNT(DISTINCT sa.canonical_id) AS unique_answered,
                       COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct
                FROM session_answers sa
                LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
                WHERE sa.user_id = ?
                GROUP BY COALESCE(cq.category_id, 0)
                """.strip(),
                [user_id],
            ),
            (
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id,
                       COUNT(*) AS active_mistakes
                FROM user_mistakes um
                LEFT JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
                WHERE um.user_id = ? AND um.is_resolved = 0
                GROUP BY COALESCE(cq.category_id, 0)
                """.strip(),
                [user_id],
            ),
            (
                """
                SELECT
                    (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
                    (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
                    (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS unresolved_mistakes,
                    (SELECT COALESCE(SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS resolved_mistakes,
                    (SELECT current_streak FROM learning_streak WHERE user_id = ?) AS current_streak,
                    (SELECT last_active_date FROM learning_streak WHERE user_id = ?) AS last_active_date,
                    (SELECT daily_goal_questions FROM learning_streak WHERE user_id = ?) AS daily_goal_questions,
                    (SELECT today_questions_count FROM learning_streak WHERE user_id = ?) AS today_questions_count,
                    (SELECT COUNT(*) FROM user_completed_modules WHERE user_id = ?) AS completed_modules,
                    (SELECT COUNT(*) FROM user_ticket_progress WHERE user_id = ? AND is_passed = 1) AS passed_tickets
                """.strip(),
                [user_id] * 10,
            ),
            self._srs.build_aggregate_stmt(user_id, now_iso=now_ts),
        ]
        with self._get_connection() as conn:
            batches = self._batch_read(conn, stmts)

        summary_row = batches[2][0] if batches[2] else {}
        streak_info, _ = self._normalize_streak_row(user_id, summary_row, now_ts)
        srs_agg = self._srs.parse_aggregate_row(batches[3][0] if batches[3] else {})
        return self._assemble_analytics_payload(
            categories=categories,
            cat_perf_rows=batches[0],
            cat_mistakes_rows=batches[1],
            scalar_row=summary_row,
            srs_agg=srs_agg,
            streak_val=streak_info["current_streak"],
            engine_total_questions=engine_total_questions,
        )

    def get_user_full_auth_bundle(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        default_lang: str = "uz_latn",
        categories: Optional[List[Dict[str, Any]]] = None,
        engine_total_questions: int = 1327,
    ) -> Dict[str, Any]:
        """
        Single-connection bootstrap bundle (<= 2 Turso RTs) returning user, subscription,
        free_tier, streak (UTC+5), stats, bookmarks_count, history, analytics, and ai_usage_today.
        """
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()
        today_str = tashkent_today_str()

        metrics_stmts = self._build_metrics_queries(user_id, today_str)
        read_stmts: List[Tuple[str, List[Any]]] = [
            (
                """
                SELECT u.*, s.current_streak, s.last_active_date, s.daily_goal_questions, s.today_questions_count
                FROM telegram_users u
                LEFT JOIN learning_streak s ON u.user_id = s.user_id
                WHERE u.user_id = ?
                """.strip(),
                [user_id],
            ),
            *metrics_stmts,
            self._srs.build_aggregate_stmt(user_id, now_iso=now_ts),
            (
                """
                SELECT session_id, total_questions, correct_count, incorrect_count,
                       percentage, passed, time_taken_seconds, created_at,
                       COALESCE(unanswered_count, 0) AS unanswered_count
                FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5
                """.strip(),
                [user_id],
            ),
            (
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id,
                       COUNT(sa.id) AS total_attempts,
                       COALESCE(SUM(sa.is_correct), 0) AS correct_attempts,
                       COUNT(DISTINCT sa.canonical_id) AS unique_answered,
                       COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct
                FROM session_answers sa
                LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
                WHERE sa.user_id = ?
                GROUP BY COALESCE(cq.category_id, 0)
                """.strip(),
                [user_id],
            ),
            (
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id, COUNT(*) AS active_mistakes
                FROM user_mistakes um
                LEFT JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
                WHERE um.user_id = ? AND um.is_resolved = 0
                GROUP BY COALESCE(cq.category_id, 0)
                """.strip(),
                [user_id],
            ),
        ]

        with self._get_connection() as conn:
            batches = self._batch_read(conn, read_stmts)
            combo_row = batches[0][0] if batches[0] else None
            write_stmts: List[Any] = []

            if combo_row:
                streak_cols = {"current_streak", "last_active_date", "daily_goal_questions", "today_questions_count"}
                user_dict = {k: v for k, v in combo_row.items() if k not in streak_cols}
                subscription, sub_expired = evaluate_subscription_row(user_dict, now_ts=now_ts, now_dt=now_dt)
                if sub_expired:
                    write_stmts.append((
                        "UPDATE telegram_users SET is_pro = 0, subscription_tier = 'free' WHERE user_id = ?",
                        [user_id],
                    ))
                    user_dict["is_pro"] = 0
                    user_dict["subscription_tier"] = "free"
                user_dict["subscription"] = {
                    "is_pro": subscription["is_pro"],
                    "tier": subscription["tier"],
                    "expires_at": subscription["expires_at"],
                }
                streak, streak_sync = self._normalize_streak_row(user_id, combo_row, now_ts)
                if streak_sync:
                    write_stmts.append(streak_sync)

                last_dt = parse_iso_dt(user_dict.get("last_active_at"))
                if last_dt is None or (now_dt - last_dt).total_seconds() > 300:
                    write_stmts.append((
                        """
                        UPDATE telegram_users
                        SET username = COALESCE(?, username), first_name = COALESCE(?, first_name),
                            last_name = COALESCE(?, last_name), last_active_at = ?
                        WHERE user_id = ?
                        """.strip(),
                        [username, first_name, last_name, now_ts, user_id],
                    ))
                    user_dict["last_active_at"] = now_ts
            else:
                subscription = {
                    "is_pro": False,
                    "tier": "free",
                    "tier_name": "Oddiy tarif (Tekin)",
                    "expires_at": None,
                    "days_left": 0,
                    "is_active": False,
                }
                user_dict = {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "language": default_lang,
                    "is_language_selected": 0,
                    "is_admin": 0,
                    "is_blocked": 0,
                    "is_pro": 0,
                    "subscription_tier": "free",
                    "subscription_expires_at": None,
                    "created_at": now_ts,
                    "last_active_at": now_ts,
                    "subscription": {"is_pro": False, "tier": "free", "expires_at": None},
                }
                streak, streak_sync = self._normalize_streak_row(user_id, None, now_ts)
                write_stmts.append((
                    """
                    INSERT OR IGNORE INTO telegram_users (
                        user_id, username, first_name, last_name, language,
                        is_language_selected, is_pro, subscription_tier, created_at, last_active_at
                    ) VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                    """.strip(),
                    [user_id, username, first_name, last_name, default_lang, now_ts, now_ts],
                ))
                if streak_sync:
                    write_stmts.append(streak_sync)

            if write_stmts:
                self._batch_write(conn, write_stmts)

        ans_row = batches[1][0] if batches[1] else {}
        scalar_row = batches[2][0] if batches[2] else {}
        srs_agg = self._srs.parse_aggregate_row(batches[3][0] if batches[3] else {})
        stats = self._assemble_stats_payload(
            ans_row,
            scalar_row,
            srs_agg,
            streak_val=streak["current_streak"],
            engine_total_questions=engine_total_questions,
        )
        used_exams = stats["total_exams"] + int(scalar_row.get("active_in_progress_exams") or 0)
        free_tier = compute_free_tier_from_counts(subscription, used_exams)
        history = [
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
            for r in batches[4]
        ]

        ai_used = int(scalar_row.get("ai_usage_today") or 0)
        ai_max = 100 if subscription.get("is_pro") else 3
        ai_usage_today = {
            "current": ai_used,
            "max": ai_max,
            "remaining": max(0, ai_max - ai_used),
            "locked": (not subscription.get("is_pro")) and ai_used >= ai_max,
        }

        out: Dict[str, Any] = {
            "user": user_dict,
            "subscription": subscription,
            "free_tier": free_tier,
            "streak": streak,
            "stats": stats,
            "bookmarks_count": int(scalar_row.get("bookmarks_count") or 0),
            "history": history,
            "ai_usage_today": ai_usage_today,
        }
        if categories is not None:
            out["analytics"] = self._assemble_analytics_payload(
                categories=categories,
                cat_perf_rows=batches[5],
                cat_mistakes_rows=batches[6],
                scalar_row=scalar_row,
                srs_agg=srs_agg,
                streak_val=streak["current_streak"],
                engine_total_questions=engine_total_questions,
            )
        return out

    def get_learning_streak(self, user_id: int) -> Dict[str, Any]:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT current_streak, last_active_date, daily_goal_questions, today_questions_count FROM learning_streak WHERE user_id = ?",
                (user_id,),
            )
            row = c.fetchone()
            streak, write_stmt = self._normalize_streak_row(user_id, dict(row) if row else None, now_ts)
            if write_stmt:
                self._batch_write(conn, [write_stmt])
            return streak

    def increment_streak_progress(self, user_id: int, count: int = 1) -> Dict[str, Any]:
        info = self.get_learning_streak(user_id)
        today_str = tashkent_today_str()
        now_ts = datetime.utcnow().isoformat()
        new_today = info["today_questions_count"] + count
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE learning_streak SET today_questions_count = ?, last_active_date = ?, updated_at = ? WHERE user_id = ?",
                (new_today, today_str, now_ts, user_id),
            )
            conn.commit()
        info["today_questions_count"] = new_today
        return info

    def set_daily_goal(self, user_id: int, goal_questions: int) -> int:
        goal = max(5, min(100, int(goal_questions)))
        today_str = tashkent_today_str()
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM learning_streak WHERE user_id = ?", (user_id,))
            if c.fetchone():
                c.execute(
                    "UPDATE learning_streak SET daily_goal_questions = ?, updated_at = ? WHERE user_id = ?",
                    (goal, now_ts, user_id),
                )
            else:
                c.execute(
                    """
                    INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                    VALUES (?, 0, ?, ?, 0, ?)
                    """,
                    (user_id, today_str, goal, now_ts),
                )
            conn.commit()
        return goal

    def get_ai_full_stats_on_conn(self, conn: Any, user_id: int, engine_total_questions: int = 1327) -> Dict[str, Any]:
        """Loads stats + history LIMIT 20 in 1 batched RT using an open DB connection."""
        now_ts = datetime.utcnow().isoformat()
        today_str = tashkent_today_str()
        metrics_stmts = self._build_metrics_queries(user_id, today_str)
        stmts: List[Tuple[str, List[Any]]] = [
            ("SELECT current_streak, last_active_date, daily_goal_questions, today_questions_count FROM learning_streak WHERE user_id = ?", [user_id]),
            *metrics_stmts,
            self._srs.build_aggregate_stmt(user_id, now_iso=now_ts),
            ("SELECT correct_count, percentage FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 20", [user_id]),
        ]
        batches = self._batch_read(conn, stmts)
        streak_row = batches[0][0] if batches[0] else None
        streak_info, sync_stmt = self._normalize_streak_row(user_id, streak_row, now_ts)
        if sync_stmt:
            self._batch_write(conn, [sync_stmt])
        ans_row = batches[1][0] if batches[1] else {}
        scalar_row = batches[2][0] if batches[2] else {}
        srs_agg = self._srs.parse_aggregate_row(batches[3][0] if batches[3] else {})
        stats = self._assemble_stats_payload(
            ans_row,
            scalar_row,
            srs_agg,
            streak_val=streak_info["current_streak"],
            engine_total_questions=engine_total_questions,
        )
        history = batches[4] or []
        avg_correct = round(sum(int(h["correct_count"] or 0) for h in history) / len(history), 1) if history else 0.0
        avg_pct = round(sum(float(h["percentage"] or 0) for h in history) / len(history), 1) if history else 0.0
        return {
            "stats": stats,
            "bookmarks_count": int(scalar_row.get("bookmarks_count") or 0),
            "avg_correct": avg_correct,
            "avg_pct": avg_pct,
        }

    def get_ai_student_snapshot_on_conn(self, conn: Any, user_id: int) -> Dict[str, Any]:
        """Returns compact student telemetry synced with AnalyticsRepo using an existing DB connection."""
        stats = self.get_user_stats_on_conn(conn, user_id)
        srs = stats.get("srs_summary") or {}
        return {
            "total_exams": int(stats["total_exams"]),
            "passed_exams": int(stats["passed_exams"]),
            "pass_rate": float(stats["pass_rate"]),
            "accuracy": float(stats["accuracy"]),
            "readiness_score": float(stats["readiness_score"]),
            "active_mistakes": int(stats["unresolved_mistakes"]),
            "unique_answered": int(stats["unique_questions_tested"]),
            "catalog_coverage_pct": float(stats["catalog_coverage_pct"]),
            "srs_tracked_total": int(srs.get("tracked_count") or 0),
            "srs_due_now": int(srs.get("due_now_count") or 0),
            "srs_mastered_count": int(srs.get("mastered_count") or 0),
            "srs_learning_count": int(srs.get("learning_count") or 0),
            "srs_avg_ease_factor": float(srs.get("avg_ease_factor") or 2.5),
            "srs_retention_pct": float(srs.get("retention_rate") or 0.0),
        }

    def get_ai_student_snapshot(self, user_id: int) -> Dict[str, Any]:
        """Returns compact student telemetry synced with AnalyticsRepo single source of truth."""
        with self._get_connection() as conn:
            return self.get_ai_student_snapshot_on_conn(conn, user_id)

    def get_admin_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            batches = self._batch_read(
                conn,
                [
                    (
                        """
                        SELECT
                            (SELECT COUNT(*) FROM telegram_users) AS total_users,
                            (SELECT COUNT(*) FROM user_sessions WHERE status = 'COMPLETED') AS completed_sessions,
                            (SELECT COUNT(*) FROM exam_results) AS total_exams,
                            (SELECT COALESCE(SUM(passed), 0) FROM exam_results) AS passed_exams,
                            (SELECT COUNT(*) FROM canonical_questions) AS canonical_questions,
                            (SELECT COUNT(*) FROM canonical_translations) AS canonical_translations
                        """.strip(),
                        [],
                    ),
                    ("SELECT language, COUNT(*) AS cnt FROM telegram_users GROUP BY language", []),
                ],
            )
        row = batches[0][0] if batches[0] else {}
        total_exams = int(row.get("total_exams") or 0)
        passed_exams = int(row.get("passed_exams") or 0)
        return {
            "total_users": int(row.get("total_users") or 0),
            "users_by_language": {r["language"]: int(r["cnt"] or 0) for r in batches[1]},
            "completed_sessions": int(row.get("completed_sessions") or 0),
            "total_exams": total_exams,
            "passed_exams": passed_exams,
            "exam_pass_rate": round((passed_exams / total_exams * 100.0), 1) if total_exams > 0 else 0.0,
            "canonical_questions": int(row.get("canonical_questions") or 0),
            "canonical_translations": int(row.get("canonical_translations") or 0),
            "status": "HEALTHY",
        }

    def log_admin_action(self, admin_id: int, action: str, details: Optional[str] = None) -> None:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO admin_audit_logs (admin_id, action, details, performed_at) VALUES (?, ?, ?, ?)",
                (admin_id, action, details, now_ts),
            )
            conn.commit()
