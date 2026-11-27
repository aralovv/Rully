"""
Bot Database Repository & Data Access Layer for Telegram User Sessions,
Answers, Mistake Tracking, and Admin Analytics.
"""
import os
import secrets
import sqlite3
import json
import logging
import time
from threading import Lock
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Union, Set
from src.db_adapter import get_db_connection, is_turso_enabled, execute_batch
from src.db.scoring import compute_driver_accuracy, compute_driver_readiness
from src.db.sm2_engine import (
    build_srs_upsert_stmt,
    classify_srs_mastery,
    compute_next_sm2_state,
    derive_sm2_quality,
)
from src.security.rate_limiter import BoundedTTLCache

logger = logging.getLogger(__name__)
_PRE_ANSWER_SRS_CACHE = BoundedTTLCache[Tuple[int, str], Optional[Dict[str, Any]]](maxsize=4000, ttl_seconds=900.0)

# --- Subscription Plans Specification ---
SUBSCRIPTION_PLANS = {
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
    }
}


class BotDatabase:
    _ticket_schema_ready: bool = False
    _ticket_ready_paths: Set[str] = set()
    _srs_ready_paths: Set[str] = set()
    _schema_lock: Lock = Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "master_database.sqlite")
        if not is_turso_enabled():
            self._init_bot_schema()

    def _ensure_srs_schema(self, conn) -> None:
        key = "__turso__" if is_turso_enabled() else os.path.abspath(self.db_path)
        with BotDatabase._schema_lock:
            if key in BotDatabase._srs_ready_paths:
                return
        try:
            execute_batch(
                conn,
                [
                    """
                    CREATE TABLE IF NOT EXISTS user_question_srs (
                        user_id INTEGER NOT NULL,
                        canonical_id TEXT NOT NULL,
                        ease_factor REAL NOT NULL DEFAULT 2.5,
                        interval_days INTEGER NOT NULL DEFAULT 0,
                        repetitions INTEGER NOT NULL DEFAULT 0,
                        lapses INTEGER NOT NULL DEFAULT 0,
                        last_quality INTEGER NOT NULL DEFAULT 0,
                        last_reviewed_at TEXT NOT NULL,
                        next_review_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, canonical_id),
                        FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
                    )
                    """.strip(),
                    "CREATE INDEX IF NOT EXISTS idx_srs_user_due ON user_question_srs(user_id, next_review_at)",
                    "CREATE INDEX IF NOT EXISTS idx_srs_user_reps ON user_question_srs(user_id, repetitions, lapses)",
                ],
            )
            with BotDatabase._schema_lock:
                BotDatabase._srs_ready_paths.add(key)
        except Exception as exc:
            logger.warning("SRS lazy schema sync failed cleanly: %s", exc)

    def _ensure_ticket_progress_table(self, conn) -> None:
        key = "__turso__" if is_turso_enabled() else os.path.abspath(self.db_path)
        with BotDatabase._schema_lock:
            if BotDatabase._ticket_schema_ready and key in BotDatabase._ticket_ready_paths:
                return
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(session_answers)")
            sa_cols = {
                r["name"] if hasattr(r, "keys") and "name" in r.keys() else r[1]
                for r in cur.fetchall()
            }
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS user_ticket_progress (
                    user_id INTEGER NOT NULL,
                    ticket_number INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL DEFAULT 20,
                    best_correct INTEGER NOT NULL DEFAULT 0,
                    best_percentage REAL NOT NULL DEFAULT 0.0,
                    attempts_count INTEGER NOT NULL DEFAULT 1,
                    is_passed INTEGER NOT NULL DEFAULT 0,
                    last_session_id TEXT,
                    last_attempted_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, ticket_number),
                    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_ticket_progress_user ON user_ticket_progress(user_id)",
            ]
            if "user_id" not in sa_cols:
                stmts.append("ALTER TABLE session_answers ADD COLUMN user_id INTEGER DEFAULT NULL")
            stmts.append("CREATE INDEX IF NOT EXISTS idx_session_answers_user_canon ON session_answers(user_id, canonical_id, is_correct)")
            stmts.append("CREATE INDEX IF NOT EXISTS idx_session_answers_user_recent ON session_answers(user_id, id DESC)")
            stmts.append("""
                UPDATE session_answers
                SET user_id = (SELECT user_id FROM user_sessions WHERE user_sessions.session_id = session_answers.session_id)
                WHERE user_id IS NULL
            """.strip())
            execute_batch(conn, stmts)
            with BotDatabase._schema_lock:
                BotDatabase._ticket_schema_ready = True
                BotDatabase._ticket_ready_paths.add(key)
        except Exception as exc:
            logger.warning("Ticket progress lazy schema sync failed cleanly: %s", exc)

    def _get_connection(self):
        return get_db_connection(self.db_path)

    def _init_bot_schema(self):
        with self._get_connection() as conn:
            c = conn.cursor()

            # 1. Telegram users
            c.execute("""
            CREATE TABLE IF NOT EXISTS telegram_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT NOT NULL DEFAULT 'uz_latn',
                is_language_selected INTEGER NOT NULL DEFAULT 0,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_active_at TEXT NOT NULL
            );
            """)

            # 2. User sessions (Exams, category practice, quick tests)
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_type TEXT NOT NULL,
                category_id INTEGER,
                language TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                current_index INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                incorrect_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
                start_time REAL NOT NULL,
                time_limit_seconds INTEGER NOT NULL DEFAULT 0,
                deadline REAL,
                question_ids_json TEXT NOT NULL,
                active_message_id INTEGER,
                show_answer INTEGER NOT NULL DEFAULT 1,
                show_explanation INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # Safe column migration for existing tables
            try:
                c.execute("ALTER TABLE user_sessions ADD COLUMN show_answer INTEGER NOT NULL DEFAULT 1")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE user_sessions ADD COLUMN show_explanation INTEGER NOT NULL DEFAULT 1")
            except Exception:
                pass

            # 3. Session answers (Stores user answers with UNIQUE constraint preventing double submission)
            c.execute("""
            CREATE TABLE IF NOT EXISTS session_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                canonical_id TEXT NOT NULL,
                selected_key TEXT NOT NULL,
                correct_key TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
                UNIQUE(session_id, canonical_id)
            );
            """)

            # 4. User mistakes ("Xatolarim" pool)
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                canonical_id TEXT NOT NULL,
                mistake_count INTEGER NOT NULL DEFAULT 1,
                last_mistake_at TEXT NOT NULL,
                is_resolved INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
                UNIQUE(user_id, canonical_id)
            );
            """)

            # 5. Exam results history
            c.execute("""
            CREATE TABLE IF NOT EXISTS exam_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                incorrect_count INTEGER NOT NULL,
                percentage REAL NOT NULL,
                passed INTEGER NOT NULL,
                time_taken_seconds REAL NOT NULL,
                category_breakdown_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                unanswered_count INTEGER DEFAULT 0,
                FOREIGN KEY(session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # Non-destructive migration for existing installations
            try:
                c.execute("ALTER TABLE exam_results ADD COLUMN unanswered_count INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("ALTER TABLE telegram_users ADD COLUMN is_language_selected INTEGER NOT NULL DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("""
                    UPDATE telegram_users 
                    SET is_language_selected = 1 
                    WHERE user_id IN (SELECT user_id FROM user_sessions UNION SELECT user_id FROM exam_results)
                """)
                conn.commit()
            except sqlite3.OperationalError:
                pass

            # 6. Admin audit logs
            c.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                performed_at TEXT NOT NULL
            );
            """)

            # 7. User bookmarks
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                canonical_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
                UNIQUE(user_id, canonical_id)
            );
            """)

            # 8. Practical Exam Checklist
            c.execute("""
            CREATE TABLE IF NOT EXISTS practical_checklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, item_id)
            );
            """)

            # 9. Practical Situational Quiz Results
            c.execute("""
            CREATE TABLE IF NOT EXISTS practical_quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                scenario_id TEXT NOT NULL,
                selected_option INTEGER NOT NULL,
                is_correct INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # 10. Learning Streak & Daily Goals
            c.execute("""
            CREATE TABLE IF NOT EXISTS learning_streak (
                user_id INTEGER PRIMARY KEY,
                current_streak INTEGER NOT NULL DEFAULT 1,
                last_active_date TEXT NOT NULL,
                daily_goal_questions INTEGER NOT NULL DEFAULT 20,
                today_questions_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # 11. User Completed Practical Modules
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_completed_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                module_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, module_id)
            );
            """)

            # 12. User Subscriptions (PRO Monitazation)
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                price_uzs INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # Non-destructive migrations for subscription fields on telegram_users
            try:
                c.execute("ALTER TABLE telegram_users ADD COLUMN is_pro INTEGER NOT NULL DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE telegram_users ADD COLUMN subscription_tier TEXT NOT NULL DEFAULT 'free'")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE telegram_users ADD COLUMN subscription_expires_at TEXT DEFAULT NULL")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE session_answers ADD COLUMN user_id INTEGER DEFAULT NULL")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            # 13. Ticket (Bilet) Progress
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_ticket_progress (
                user_id INTEGER NOT NULL,
                ticket_number INTEGER NOT NULL,
                total_questions INTEGER NOT NULL DEFAULT 20,
                best_correct INTEGER NOT NULL DEFAULT 0,
                best_percentage REAL NOT NULL DEFAULT 0.0,
                attempts_count INTEGER NOT NULL DEFAULT 1,
                is_passed INTEGER NOT NULL DEFAULT 0,
                last_session_id TEXT,
                last_attempted_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticket_number),
                FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
            );
            """)

            # 14. SM-2 Spaced Repetition Schedule (Phase 5)
            c.execute("""
            CREATE TABLE IF NOT EXISTS user_question_srs (
                user_id INTEGER NOT NULL,
                canonical_id TEXT NOT NULL,
                ease_factor REAL NOT NULL DEFAULT 2.5,
                interval_days INTEGER NOT NULL DEFAULT 0,
                repetitions INTEGER NOT NULL DEFAULT 0,
                lapses INTEGER NOT NULL DEFAULT 0,
                last_quality INTEGER NOT NULL DEFAULT 0,
                last_reviewed_at TEXT NOT NULL,
                next_review_at TEXT NOT NULL,
                PRIMARY KEY (user_id, canonical_id),
                FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
            );
            """)

            # Performance indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_checklist_user ON practical_checklist(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_modules_user ON user_completed_modules(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subs_user ON user_subscriptions(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON user_sessions(user_id, status);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_exam_results_user ON exam_results(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_answers_session ON session_answers(session_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_session_answers_user_recent ON session_answers(user_id, id DESC);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_ticket_progress_user ON user_ticket_progress(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_session_answers_user_canon ON session_answers(user_id, canonical_id, is_correct);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_srs_user_due ON user_question_srs(user_id, next_review_at);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_srs_user_reps ON user_question_srs(user_id, repetitions, lapses);")

            try:
                c.execute("""
                    UPDATE session_answers
                    SET user_id = (SELECT user_id FROM user_sessions WHERE user_sessions.session_id = session_answers.session_id)
                    WHERE user_id IS NULL
                """)
            except Exception:
                pass
            conn.commit()
            with BotDatabase._schema_lock:
                BotDatabase._ticket_schema_ready = True
                BotDatabase._ticket_ready_paths.add(os.path.abspath(self.db_path))
                BotDatabase._srs_ready_paths.add(os.path.abspath(self.db_path))

    # --- User Management ---
    def get_or_create_user(self, user_id: int, username: Optional[str] = None,
                           first_name: Optional[str] = None, last_name: Optional[str] = None,
                           default_lang: str = "uz_latn") -> Dict[str, Any]:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                user_dict = dict(row)
                # Compute active subscription directly from cached user columns
                is_pro = bool(user_dict.get("is_pro", 0))
                sub_exp = user_dict.get("subscription_expires_at")
                if is_pro and sub_exp and sub_exp > now_ts:
                    user_dict["subscription"] = {
                        "is_pro": True,
                        "tier": user_dict.get("subscription_tier", "pro"),
                        "expires_at": sub_exp
                    }
                else:
                    user_dict["subscription"] = {
                        "is_pro": False,
                        "tier": "free",
                        "expires_at": None
                    }

                # Throttle last_active_at updates to once every 5 minutes to avoid redundant DB roundtrips
                last_act = user_dict.get("last_active_at")
                needs_update = False
                if not last_act:
                    needs_update = True
                else:
                    try:
                        diff = (datetime.utcnow() - datetime.fromisoformat(last_act.replace("Z", ""))).total_seconds()
                        if diff > 300:
                            needs_update = True
                    except Exception:
                        needs_update = True

                if needs_update:
                    c.execute("""
                    UPDATE telegram_users
                    SET username = COALESCE(?, username), first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name), last_active_at = ?
                    WHERE user_id = ?
                    """, (username, first_name, last_name, now_ts, user_id))
                    user_dict["last_active_at"] = now_ts
                    conn.commit()

                return user_dict
            else:
                c.execute("""
                INSERT INTO telegram_users (user_id, username, first_name, last_name, language, is_language_selected, is_pro, subscription_tier, created_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                """, (user_id, username, first_name, last_name, default_lang, now_ts, now_ts))
                conn.commit()
                c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
                user_dict = dict(c.fetchone())
                user_dict["subscription"] = {"is_pro": False, "tier": "free", "expires_at": None}
                return user_dict

    def get_user_full_auth_bundle(self, user_id: int, username: Optional[str] = None,
                                  first_name: Optional[str] = None, last_name: Optional[str] = None,
                                  default_lang: str = "uz_latn") -> Dict[str, Any]:
        """
        Ultra-fast single-connection bootstrap bundle for Telegram Mini App auth.
        Fetches user, active subscription, learning streak, stats, and free tier
        in just 2 combined round-trips (~700ms total) instead of 12 separate DB network calls.
        """
        now_ts = datetime.utcnow().isoformat()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            c = conn.cursor()

            # 1. User & Learning Streak in a single query
            c.execute("""
            SELECT 
                u.*,
                s.current_streak,
                s.last_active_date,
                s.daily_goal_questions,
                s.today_questions_count
            FROM telegram_users u
            LEFT JOIN learning_streak s ON u.user_id = s.user_id
            WHERE u.user_id = ?
            """, (user_id,))
            combo_row = c.fetchone()

            if combo_row:
                user_dict = {k: v for k, v in dict(combo_row).items() if k not in ['current_streak', 'last_active_date', 'daily_goal_questions', 'today_questions_count']}
                is_pro = bool(user_dict.get("is_pro", 0))
                sub_exp = user_dict.get("subscription_expires_at")
                if is_pro and sub_exp and sub_exp > now_ts:
                    subscription = {
                        "is_pro": True,
                        "tier": user_dict.get("subscription_tier", "pro"),
                        "expires_at": sub_exp
                    }
                else:
                    subscription = {
                        "is_pro": False,
                        "tier": "free",
                        "expires_at": None
                    }
                user_dict["subscription"] = subscription

                # Check streak from joined columns
                strk_val = combo_row["current_streak"]
                last_date = combo_row["last_active_date"]
                goal = combo_row["daily_goal_questions"]
                today_count = combo_row["today_questions_count"]
                if strk_val is None:
                    c.execute("""
                    INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                    VALUES (?, 0, ?, 20, 0, ?)
                    """, (user_id, today_str, now_ts))
                    streak = {
                        "current_streak": 0,
                        "last_active_date": today_str,
                        "daily_goal_questions": 20,
                        "today_questions_count": 0
                    }
                else:
                    if last_date != today_str:
                        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                        if last_date != yesterday_str:
                            strk_val = 0
                        today_count = 0
                    streak = {
                        "current_streak": strk_val,
                        "last_active_date": last_date,
                        "daily_goal_questions": goal or 20,
                        "today_questions_count": today_count or 0
                    }

                # Throttle last_active_at update (at most once per 5 minutes)
                last_act = user_dict.get("last_active_at")
                needs_update = not last_act
                if last_act:
                    try:
                        diff = (datetime.utcnow() - datetime.fromisoformat(last_act.replace("Z", ""))).total_seconds()
                        if diff > 300:
                            needs_update = True
                    except Exception:
                        needs_update = True
                if needs_update:
                    c.execute("""
                    UPDATE telegram_users
                    SET username = COALESCE(?, username), first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name), last_active_at = ?
                    WHERE user_id = ?
                    """, (username, first_name, last_name, now_ts, user_id))
                    user_dict["last_active_at"] = now_ts
            else:
                # Brand new user bootstrap
                c.execute("""
                INSERT INTO telegram_users (user_id, username, first_name, last_name, language, is_language_selected, is_pro, subscription_tier, created_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                """, (user_id, username, first_name, last_name, default_lang, now_ts, now_ts))
                c.execute("""
                INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                VALUES (?, 0, ?, 20, 0, ?)
                """, (user_id, today_str, now_ts))
                c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
                user_dict = dict(c.fetchone())
                subscription = {
                    "is_pro": False,
                    "tier": "free",
                    "expires_at": None
                }
                user_dict["subscription"] = subscription
                streak = {
                    "current_streak": 0,
                    "last_active_date": today_str,
                    "daily_goal_questions": 20,
                    "today_questions_count": 0
                }

            # 2. Consolidated Telemetry & Free Tier Metrics (single indexed stats pass)
            stats_row = self._query_user_core_metrics(conn, user_id, include_active_exams=True)
            srs_agg = self._query_srs_aggregate(conn, user_id, now_iso=now_ts)

            total_exams = stats_row.get("total_exams") or 0
            passed_exams = stats_row.get("passed_exams") or 0
            total_ans = stats_row.get("total_ans") or 0
            correct_ans = stats_row.get("correct_ans") or 0
            mistakes_cnt = stats_row.get("unresolved_mistakes") or 0
            resolved_cnt = stats_row.get("resolved_mistakes") or 0
            unique_qs = stats_row.get("unique_qs") or 0
            categories_tested = stats_row.get("categories_tested") or 0
            unique_correct = stats_row.get("unique_correct") or 0
            active_unfin = stats_row.get("active_in_progress_exams") or 0

            recent_exams_count = stats_row.get("recent_exams_count") or 0
            recent_exams_passed = stats_row.get("recent_exams_passed") or 0
            recent_pass_rate = round(recent_exams_passed / recent_exams_count * 100.0, 1) if recent_exams_count > 0 else None
            avg_exam_time = float(stats_row.get("recent_avg_exam_time") or 0.0)
            recent_ans_total = int(stats_row.get("recent_ans_total") or 0)
            recent_ans_correct = int(stats_row.get("recent_ans_correct") or 0)

            pass_rate = round((passed_exams / total_exams * 100), 1) if total_exams > 0 else 0.0
            accuracy_info = compute_driver_accuracy(
                total_answered=total_ans,
                correct_answers=correct_ans,
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
                total_answered=total_ans,
                accuracy=accuracy,
                unique_questions=unique_qs,
                unresolved_mistakes=mistakes_cnt,
                categories_tested=categories_tested,
                resolved_mistakes=resolved_cnt,
                current_streak=streak["current_streak"],
                avg_exam_time_seconds=avg_exam_time,
                recent_pass_rate=recent_pass_rate,
                return_details=True,
                srs_mastered=srs_agg["mastered_count"],
                srs_due=srs_agg["due_now_count"],
                srs_tracked=srs_agg["tracked_count"],
            )

            stats = {
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
                "categories_tested": categories_tested,
                "streak": streak["current_streak"],
                "avg_exam_time_seconds": round(avg_exam_time, 1),
                "readiness_score": readiness_info["readiness_score"],
                "readiness_grade": readiness_info["grade"],
                "readiness_pillars": readiness_info["pillars"]
            }

            # 3. Free Tier (Zero extra queries!)
            if subscription.get("is_pro"):
                free_tier = {
                    "is_pro": True,
                    "has_access": True,
                    "free_tier_active": False,
                    "allowed_exams": 2,
                    "used_exams": 0,
                    "remaining_exams": 999999
                }
            else:
                used_exams = total_exams + active_unfin
                remaining = max(0, 2 - used_exams)
                free_tier = {
                    "is_pro": False,
                    "has_access": remaining > 0,
                    "free_tier_active": remaining > 0,
                    "allowed_exams": 2,
                    "used_exams": used_exams,
                    "remaining_exams": remaining
                }

            conn.commit()

            return {
                "user": user_dict,
                "subscription": subscription,
                "free_tier": free_tier,
                "streak": streak,
                "stats": stats
            }

    def set_user_language(self, user_id: int, language: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE telegram_users SET language = ?, is_language_selected = 1 WHERE user_id = ?", (language, user_id))
            conn.commit()
            return c.rowcount > 0

    def has_user_selected_language(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT is_language_selected FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                return bool(row["is_language_selected"])
            return False

    def get_user_language(self, user_id: int) -> str:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT language FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return row["language"] if row else "uz_latn"

    # --- Subscription & Monetization Management ---
    def get_user_subscription(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves live subscription status for a user, validating expiration timestamps.
        Automatically downgrades expired PRO subscriptions back to free.
        """
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT is_pro, subscription_tier, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                return {
                    "is_pro": False,
                    "tier": "free",
                    "tier_name": "Oddiy tarif (Tekin)",
                    "expires_at": None,
                    "days_left": 0,
                    "is_active": False
                }

            is_pro = bool(row["is_pro"])
            tier = row["subscription_tier"] or "free"
            expires_at_str = row["subscription_expires_at"]

            if is_pro and expires_at_str:
                try:
                    expires_dt = datetime.fromisoformat(expires_at_str.replace("Z", ""))
                    now_dt = datetime.utcnow()
                    if expires_dt > now_dt:
                        diff = expires_dt - now_dt
                        days_left = diff.days + (1 if diff.seconds > 0 else 0)
                        tier_name = "PRO (14 kunlik)" if "14" in tier else "PRO (30 kunlik)"
                        return {
                            "is_pro": True,
                            "tier": tier,
                            "tier_name": tier_name,
                            "expires_at": expires_at_str,
                            "days_left": max(1, days_left),
                            "is_active": True
                        }
                    else:
                        # Expired: update user in DB back to free tier
                        c.execute("UPDATE telegram_users SET is_pro = 0, subscription_tier = 'free' WHERE user_id = ?", (user_id,))
                        conn.commit()
                except Exception:
                    pass

            return {
                "is_pro": False,
                "tier": "free",
                "tier_name": "Oddiy tarif (Tekin)",
                "expires_at": None,
                "days_left": 0,
                "is_active": False
            }

    def get_user_exam_count(self, user_id: int) -> int:
        """
        Returns count of completed or substantially attempted EXAM sessions for the user.
        Counts:
        1. Finished exams recorded in exam_results.
        2. Any active/unfinalized session of type 'EXAM' that has >= 3 answers recorded.
        """
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM exam_results WHERE user_id = ?", (user_id,))
            finished = (c.fetchone()[0] or 0)

            c.execute("""
            SELECT COUNT(DISTINCT us.session_id)
            FROM user_sessions us
            JOIN session_answers sa ON us.session_id = sa.session_id
            LEFT JOIN exam_results er ON us.session_id = er.session_id
            WHERE us.user_id = ? AND us.session_type = 'EXAM' AND er.id IS NULL
            GROUP BY us.session_id
            HAVING COUNT(sa.id) >= 3
            """, (user_id,))
            rows = c.fetchall()
            unfinished = len(rows)
            return finished + unfinished

    def get_user_free_tier_status(self, user_id: int, subscription: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluates Free Tier access for the user:
        - 2 free official state exam attempts are provided to all new users.
        - PRO subscribers have unlimited access.
        """
        sub = subscription if subscription is not None else self.get_user_subscription(user_id)
        if sub.get("is_pro"):
            return {
                "is_pro": True,
                "has_access": True,
                "free_tier_active": False,
                "allowed_exams": 2,
                "used_exams": 0,
                "remaining_exams": 999999
            }

        used_exams = self.get_user_exam_count(user_id)
        remaining = max(0, 2 - used_exams)
        has_access = (remaining > 0)
        return {
            "is_pro": False,
            "has_access": has_access,
            "free_tier_active": has_access,
            "allowed_exams": 2,
            "used_exams": used_exams,
            "remaining_exams": remaining
        }

    def get_user_answered_count(self, user_id: int) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT COUNT(*)
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            WHERE us.user_id = ?
            """, (user_id,))
            row = c.fetchone()
            return (row[0] or 0) if row else 0

    def activate_subscription(self, user_id: int, plan_id: str) -> Dict[str, Any]:
        """
        Activates or extends a PRO subscription (14 days / 14 000 UZS or 30 days / 25 000 UZS).
        If the user already has an active PRO subscription, extends from their existing expiration.
        """
        plan_key = "pro_14" if "14" in str(plan_id) else "pro_30"
        plan = SUBSCRIPTION_PLANS.get(plan_key, SUBSCRIPTION_PLANS["pro_14"])
        now_dt = datetime.utcnow()

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT is_pro, subscription_expires_at FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()

            base_dt = now_dt
            if row and row["is_pro"] and row["subscription_expires_at"]:
                try:
                    current_exp = datetime.fromisoformat(row["subscription_expires_at"].replace("Z", ""))
                    if current_exp > now_dt:
                        base_dt = current_exp
                except Exception:
                    pass

            new_expires_dt = base_dt + timedelta(days=plan["duration_days"])
            new_expires_str = new_expires_dt.isoformat()
            now_str = now_dt.isoformat()

            c.execute("""
                UPDATE telegram_users
                SET is_pro = 1, subscription_tier = ?, subscription_expires_at = ?
                WHERE user_id = ?
            """, (plan["id"], new_expires_str, user_id))

            c.execute("""
                INSERT INTO user_subscriptions (
                    user_id, plan_id, plan_name, duration_days, price_uzs, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            """, (user_id, plan["id"], plan["name"], plan["duration_days"], plan["price_uzs"], now_str, new_expires_str))

            conn.commit()

        return self.get_user_subscription(user_id)

    # --- Session Management ---
    def create_session(self, user_id: int, session_type: str, language: str,
                       question_ids: List[str], time_limit_seconds: int = 0,
                       category_id: Optional[int] = None,
                       show_answer: bool = True,
                       show_explanation: bool = True) -> Dict[str, Any]:
        session_id = f"SES-{int(time.time() * 1000)}-{user_id}-{secrets.token_hex(2)}"
        now_ts = datetime.utcnow().isoformat()
        start_t = time.time()
        deadline = (start_t + time_limit_seconds) if time_limit_seconds > 0 else None

        with self._get_connection() as conn:
            # Batch abort of existing session + insert of new session in a single round-trip
            batch_stmts = [
                ("UPDATE user_sessions SET status = 'ABORTED' WHERE user_id = ? AND status = 'IN_PROGRESS'", [user_id]),
                ("""
                INSERT INTO user_sessions (
                    session_id, user_id, session_type, category_id, language,
                    total_questions, current_index, correct_count, incorrect_count,
                    status, start_time, time_limit_seconds, deadline, question_ids_json,
                    show_answer, show_explanation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 'IN_PROGRESS', ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    session_id, user_id, session_type, category_id, language,
                    len(question_ids), start_t, time_limit_seconds, deadline,
                    json.dumps(question_ids), 1 if show_answer else 0, 1 if show_explanation else 0,
                    now_ts, now_ts
                ])
            ]
            execute_batch(conn, batch_stmts)

            c = conn.cursor()
            # Also fetch bookmark IDs inside the same connection to save network roundtrip
            c.execute("SELECT canonical_id FROM user_bookmarks WHERE user_id = ?", (user_id,))
            bm_ids = [r["canonical_id"] for r in c.fetchall()]
            conn.commit()

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
            "bookmark_ids": set(bm_ids)
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
            c.execute("""
            SELECT * FROM user_sessions
            WHERE user_id = ? AND status = 'IN_PROGRESS'
            ORDER BY start_time DESC LIMIT 1
            """, (user_id,))
            row = c.fetchone()
            if not row:
                return None
            res = dict(row)
            res["question_ids"] = json.loads(res["question_ids_json"])
            res["show_answer"] = bool(res.get("show_answer", 1))
            res["show_explanation"] = bool(res.get("show_explanation", 1))
            return res

    def save_answer(self, session_id: str, canonical_id: str,
                    selected_key: str, correct_key: str, is_correct: bool) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute("""
                INSERT INTO session_answers (
                    session_id, user_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                ) VALUES (
                    ?, (SELECT user_id FROM user_sessions WHERE session_id = ? LIMIT 1), ?, ?, ?, ?, ?
                )
                """, (session_id, session_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts))
            except sqlite3.IntegrityError:
                # Already answered, idempotent duplicate protection!
                return False

            # Update session score
            if is_correct:
                c.execute("UPDATE user_sessions SET correct_count = correct_count + 1, updated_at = ? WHERE session_id = ?", (now_ts, session_id))
            else:
                c.execute("UPDATE user_sessions SET incorrect_count = incorrect_count + 1, updated_at = ? WHERE session_id = ?", (now_ts, session_id))
            conn.commit()
            return True

    def process_session_answer(self, session_id: str, user_id: int, canonical_id: str,
                               selected_key: str, correct_key: str, is_correct: bool,
                               session_type: str = "EXAM",
                               response_time_ms: Optional[int] = None,
                               quality: Optional[int] = None) -> Dict[str, Any]:
        """
        Atomic execution for answer submission, mistake tracking, streak update,
        SM-2 spaced-repetition scheduling update, and exam termination check.
        Uses execute_batch() to group all write operations into a single Turso HTTP round-trip.
        """
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()
        today_str = now_dt.strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
            c = conn.cursor()

            # Guard: If EXAM session already reached 3 mistakes or was terminated, reject further answers
            if session_type == "EXAM":
                c.execute("SELECT status, incorrect_count FROM user_sessions WHERE session_id = ?", (session_id,))
                sess_row = c.fetchone()
                if sess_row and (sess_row["status"] in ("FAILED_MISTAKES", "COMPLETED", "TERMINATED") or (sess_row["incorrect_count"] or 0) >= 3):
                    return {
                        "is_new": False,
                        "streak": {"current_streak": 0, "today_questions_count": 0},
                        "is_exam_terminated": True,
                        "srs": None,
                    }
            else:
                c.execute("SELECT status, incorrect_count FROM user_sessions WHERE session_id = ?", (session_id,))
                sess_row = c.fetchone()

            # Fetch existing SM-2 state for (user_id, canonical_id)
            c.execute(
                """
                SELECT ease_factor, interval_days, repetitions, lapses, last_quality, last_reviewed_at, next_review_at
                FROM user_question_srs
                WHERE user_id = ? AND canonical_id = ?
                """,
                (user_id, canonical_id),
            )
            srs_row = c.fetchone()
            prev_srs = dict(srs_row) if srs_row else None

            # Check if this question was already answered to guarantee idempotency
            c.execute("SELECT is_correct FROM session_answers WHERE session_id = ? AND canonical_id = ?", (session_id, canonical_id))
            if c.fetchone() is not None:
                c.execute("SELECT current_streak, today_questions_count FROM learning_streak WHERE user_id = ?", (user_id,))
                st_row = c.fetchone()
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
                        "current_streak": st_row["current_streak"] if st_row else 1,
                        "today_questions_count": st_row["today_questions_count"] if st_row else 1
                    },
                    "is_exam_terminated": (sess_row["status"] == "FAILED_MISTAKES") if sess_row else False,
                    "srs": cur_srs,
                }

            # Fetch streak state to calculate updated consecutive-day streak & daily count
            c.execute("SELECT current_streak, today_questions_count, last_active_date, daily_goal_questions FROM learning_streak WHERE user_id = ?", (user_id,))
            st_row = c.fetchone()
            yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            if st_row:
                last_date = st_row["last_active_date"]
                prev_streak = st_row["current_streak"] or 0
                goal_q = st_row["daily_goal_questions"] or 20
                if last_date == today_str:
                    new_streak = max(1, prev_streak)
                    new_today = (st_row["today_questions_count"] or 0) + 1
                elif last_date == yesterday_str:
                    new_streak = max(1, prev_streak + 1)
                    new_today = 1
                else:
                    new_streak = 1
                    new_today = 1

                streak_info = {
                    "current_streak": new_streak,
                    "today_questions_count": new_today,
                    "daily_goal_questions": goal_q
                }
                streak_stmt = (
                    "UPDATE learning_streak SET current_streak = ?, today_questions_count = ?, last_active_date = ?, updated_at = ? WHERE user_id = ?",
                    [new_streak, new_today, today_str, now_ts, user_id]
                )
            else:
                streak_info = {
                    "current_streak": 1,
                    "today_questions_count": 1,
                    "daily_goal_questions": 20
                }
                streak_stmt = (
                    """
                    INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                    VALUES (?, 1, ?, 20, 1, ?)
                    """,
                    [user_id, today_str, now_ts]
                )

            # Determine exam termination condition
            curr_incorrect = (sess_row["incorrect_count"] or 0) if sess_row else 0
            new_incorrect = curr_incorrect + (0 if is_correct else 1)
            is_exam_terminated = (session_type == "EXAM" and new_incorrect >= 3)

            # Save pre-answer SM-2 snapshot so optional explicit user confidence rating recalibrates without double-counting
            _PRE_ANSWER_SRS_CACHE.set((user_id, canonical_id), prev_srs)

            # Calculate SM-2 memory transition
            derived_q = derive_sm2_quality(
                is_correct=is_correct,
                session_type=session_type,
                response_time_ms=response_time_ms,
                previous_lapses=int(prev_srs.get("lapses") or 0) if prev_srs else 0,
                explicit_quality=quality,
            )
            next_srs = compute_next_sm2_state(prev_srs, quality=derived_q, now=now_dt)

            # Build batch containing all write operations
            batch_stmts = [
                ("""
                INSERT INTO session_answers (
                    session_id, user_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [session_id, user_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts])
            ]

            if is_correct:
                batch_stmts.append((
                    "UPDATE user_sessions SET correct_count = correct_count + 1, updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id]
                ))
                batch_stmts.append((
                    "UPDATE user_mistakes SET is_resolved = 1 WHERE user_id = ? AND canonical_id = ?",
                    [user_id, canonical_id]
                ))
            else:
                batch_stmts.append((
                    "UPDATE user_sessions SET incorrect_count = incorrect_count + 1, updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id]
                ))
                batch_stmts.append((
                    """
                    INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, last_mistake_at, is_resolved)
                    VALUES (?, ?, 1, ?, 0)
                    ON CONFLICT(user_id, canonical_id) DO UPDATE SET
                        mistake_count = mistake_count + 1,
                        last_mistake_at = excluded.last_mistake_at,
                        is_resolved = 0;
                    """,
                    [user_id, canonical_id, now_ts]
                ))

            batch_stmts.append(streak_stmt)
            batch_stmts.append(build_srs_upsert_stmt(user_id, canonical_id, next_srs))

            if is_exam_terminated:
                batch_stmts.append((
                    "UPDATE user_sessions SET status = 'FAILED_MISTAKES', updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id]
                ))

            execute_batch(conn, batch_stmts)

            return {
                "is_new": True,
                "streak": streak_info,
                "is_exam_terminated": is_exam_terminated,
                "srs": next_srs,
            }

    def get_session_answers(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT canonical_id, selected_key, correct_key, is_correct, answered_at
            FROM session_answers
            WHERE session_id = ?
            """, (session_id,))
            res = {}
            for r in c.fetchall():
                res[r["canonical_id"]] = {
                    "selected_key": r["selected_key"],
                    "correct_key": r["correct_key"],
                    "is_correct": bool(r["is_correct"]),
                    "answered_at": r["answered_at"]
                }
            return res

    def advance_session(self, session_id: str) -> int:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_sessions SET current_index = current_index + 1, updated_at = ? WHERE session_id = ?", (now_ts, session_id))
            c.execute("SELECT current_index FROM user_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return c.fetchone()["current_index"]

    def finish_session(self, session_id: str, status: str = "COMPLETED") -> Optional[Dict[str, Any]]:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_sessions SET status = ?, updated_at = ? WHERE session_id = ?", (status, now_ts, session_id))
            conn.commit()
        return self.get_session(session_id)

    # --- Mistakes Tracking ---
    def record_mistake(self, user_id: int, canonical_id: str):
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO user_mistakes (user_id, canonical_id, mistake_count, last_mistake_at, is_resolved)
            VALUES (?, ?, 1, ?, 0)
            ON CONFLICT(user_id, canonical_id) DO UPDATE SET
                mistake_count = mistake_count + 1,
                last_mistake_at = excluded.last_mistake_at,
                is_resolved = 0;
            """, (user_id, canonical_id, now_ts))
            conn.commit()

    def resolve_mistake(self, user_id: int, canonical_id: str):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_mistakes SET is_resolved = 1 WHERE user_id = ? AND canonical_id = ?", (user_id, canonical_id))
            conn.commit()

    def get_user_mistakes(self, user_id: int, limit: int = 20) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT canonical_id FROM user_mistakes
            WHERE user_id = ? AND is_resolved = 0
            ORDER BY last_mistake_at DESC LIMIT ?
            """, (user_id, limit))
            return [r["canonical_id"] for r in c.fetchall()]

    def get_user_mistakes_count(self, user_id: int) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM user_mistakes WHERE user_id = ? AND is_resolved = 0", (user_id,))
            return c.fetchone()[0]

    # --- Exam Results History ---
    def save_exam_result(self, session_id: str, user_id: int, total_q: int,
                         correct: int, incorrect: int, pct: float,
                         passed: bool, time_spent: float, category_breakdown: Dict[str, Any],
                         unanswered: int = 0):
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT OR REPLACE INTO exam_results (
                session_id, user_id, total_questions, correct_count, incorrect_count,
                percentage, passed, time_taken_seconds, category_breakdown_json, created_at,
                unanswered_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, total_q, correct, incorrect, pct,
                1 if passed else 0, time_spent, json.dumps(category_breakdown), now_ts,
                unanswered
            ))
            conn.commit()

    def finalize_exam_session(self, session_id: str, user_id: int, total_q: int,
                              correct: int, incorrect: int, pct: float,
                              passed: bool, time_spent: float, category_breakdown: Dict[str, Any],
                              unanswered: int = 0, status: str = "COMPLETED",
                              record_exam_result: bool = True) -> Optional[Dict[str, Any]]:
        """
        Batches session completion and (for real EXAM sessions) exam_results persistence into one round-trip.
        """
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            batch_stmts: List[Any] = []
            if record_exam_result:
                batch_stmts.append((
                    """
                    INSERT OR REPLACE INTO exam_results (
                        session_id, user_id, total_questions, correct_count, incorrect_count,
                        percentage, passed, time_taken_seconds, category_breakdown_json, created_at,
                        unanswered_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        session_id, user_id, total_q, correct, incorrect, pct,
                        1 if passed else 0, time_spent, json.dumps(category_breakdown), now_ts,
                        unanswered,
                    ],
                ))
            batch_stmts.append(
                ("UPDATE user_sessions SET status = ?, updated_at = ? WHERE session_id = ?", [status, now_ts, session_id])
            )
            execute_batch(conn, batch_stmts)
        return self.get_session(session_id)

    def get_user_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT * FROM exam_results
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            res = []
            for r in c.fetchall():
                d = dict(r)
                d["category_breakdown"] = json.loads(d["category_breakdown_json"])
                res.append(d)
            return res

    def _query_srs_aggregate(self, conn: Any, user_id: int, now_iso: Optional[str] = None) -> Dict[str, Any]:
        """Returns compact SM-2 progress aggregates using a single indexed query on user_question_srs."""
        self._ensure_srs_schema(conn)
        now_ts = now_iso or datetime.utcnow().isoformat()
        end_of_day_ts = f"{now_ts[:10]}T23:59:59.999999"
        c = conn.cursor()
        c.execute(
            """
            SELECT
                COUNT(*) AS tracked_count,
                COALESCE(SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END), 0) AS due_now_count,
                COALESCE(SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END), 0) AS due_today_count,
                COALESCE(SUM(CASE WHEN repetitions <= 0 OR (repetitions = 1 AND lapses > 1) THEN 1 ELSE 0 END), 0) AS learning_count,
                COALESCE(SUM(CASE WHEN repetitions >= 3 AND interval_days >= 21 AND ease_factor >= 2.0 THEN 1 ELSE 0 END), 0) AS mastered_count,
                COALESCE(AVG(ease_factor), 2.5) AS avg_ease_factor
            FROM user_question_srs
            WHERE user_id = ?
            """,
            (now_ts, end_of_day_ts, user_id),
        )
        r = dict(c.fetchone() or {})
        tracked = int(r.get("tracked_count") or 0)
        due_now = int(r.get("due_now_count") or 0)
        due_today = int(r.get("due_today_count") or 0)
        learning = int(r.get("learning_count") or 0)
        mastered = int(r.get("mastered_count") or 0)
        reviewing = max(0, tracked - learning - mastered)
        avg_ef = round(float(r.get("avg_ease_factor") or 2.5), 2) if tracked > 0 else 2.5
        retention = round(((tracked - min(tracked, due_now)) / tracked) * 100.0, 1) if tracked > 0 else 100.0
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

    def _query_user_core_metrics(self, conn: Any, user_id: int, include_active_exams: bool = False) -> Dict[str, Any]:
        """Single indexed metrics sweep replacing 7 redundant session_answers JOIN subqueries."""
        self._ensure_ticket_progress_table(conn)
        c = conn.cursor()
        c.execute(
            """
            SELECT
                COUNT(sa.id) AS total_ans,
                COALESCE(SUM(sa.is_correct), 0) AS correct_ans,
                COUNT(DISTINCT sa.canonical_id) AS unique_qs,
                COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct,
                COUNT(DISTINCT cq.category_id) AS categories_tested
            FROM session_answers sa
            LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
            WHERE sa.user_id = ?
            """,
            (user_id,),
        )
        ans_agg = dict(c.fetchone() or {})

        extra_active_sql = (
            ", (SELECT COUNT(*) FROM user_sessions WHERE user_id = ? AND session_type = 'EXAM' AND status = 'IN_PROGRESS') AS active_in_progress_exams"
            if include_active_exams
            else ", 0 AS active_in_progress_exams"
        )
        params = tuple([user_id] * (11 if include_active_exams else 10))
        c.execute(
            f"""
            SELECT
              (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
              (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
              (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS unresolved_mistakes,
              (SELECT COALESCE(SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS resolved_mistakes,
              (SELECT COALESCE(current_streak, 0) FROM learning_streak WHERE user_id = ?) AS current_streak,
              (SELECT COUNT(*) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_count,
              (SELECT COALESCE(SUM(passed), 0) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_passed,
              (SELECT COALESCE(AVG(time_taken_seconds), 0) FROM (SELECT time_taken_seconds FROM exam_results WHERE user_id = ? AND time_taken_seconds > 0 ORDER BY id DESC LIMIT 5)) AS recent_avg_exam_time,
              (SELECT COUNT(*) FROM (SELECT is_correct FROM session_answers WHERE user_id = ? ORDER BY id DESC LIMIT 40)) AS recent_ans_total,
              (SELECT COALESCE(SUM(is_correct), 0) FROM (SELECT is_correct FROM session_answers WHERE user_id = ? ORDER BY id DESC LIMIT 40)) AS recent_ans_correct
              {extra_active_sql}
            """,
            params,
        )
        row = dict(c.fetchone() or {})
        row.update(ans_agg)
        return row

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
            row = self._query_user_core_metrics(conn, user_id, include_active_exams=False)
            srs_agg = self._query_srs_aggregate(conn, user_id, now_iso=now_ts)

            total_exams = int(row.get("total_exams") or 0)
            passed_exams = int(row.get("passed_exams") or 0)
            total_ans = int(row.get("total_ans") or 0)
            correct_ans = int(row.get("correct_ans") or 0)
            mistakes_cnt = int(row.get("unresolved_mistakes") or 0)
            resolved_cnt = int(row.get("resolved_mistakes") or 0)
            unique_qs = int(row.get("unique_qs") or 0)
            categories_tested = int(row.get("categories_tested") or 0)
            unique_correct = int(row.get("unique_correct") or 0)
            current_streak = int(row.get("current_streak") or 0)
            recent_exams_count = int(row.get("recent_exams_count") or 0)
            recent_exams_passed = int(row.get("recent_exams_passed") or 0)
            recent_pass_rate = round(recent_exams_passed / recent_exams_count * 100.0, 1) if recent_exams_count > 0 else None
            avg_exam_time = float(row.get("recent_avg_exam_time") or 0.0)
            recent_ans_total = int(row.get("recent_ans_total") or 0)
            recent_ans_correct = int(row.get("recent_ans_correct") or 0)

            pass_rate = round((passed_exams / total_exams * 100), 1) if total_exams > 0 else 0.0

            accuracy_info = compute_driver_accuracy(
                total_answered=total_ans,
                correct_answers=correct_ans,
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
                total_answered=total_ans,
                accuracy=accuracy,
                unique_questions=unique_qs,
                unresolved_mistakes=mistakes_cnt,
                categories_tested=categories_tested,
                resolved_mistakes=resolved_cnt,
                current_streak=current_streak,
                avg_exam_time_seconds=avg_exam_time,
                recent_pass_rate=recent_pass_rate,
                return_details=True,
                srs_mastered=srs_agg["mastered_count"],
                srs_due=srs_agg["due_now_count"],
                srs_tracked=srs_agg["tracked_count"],
            )

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
                "categories_tested": categories_tested,
                "streak": current_streak,
                "avg_exam_time_seconds": round(avg_exam_time, 1),
                "readiness_score": readiness_info["readiness_score"],
                "readiness_grade": readiness_info["grade"],
                "readiness_pillars": readiness_info["pillars"],
                "srs_summary": srs_agg,
            }

    # --- Admin Analytics ---
    def get_admin_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM telegram_users")
            total_users = c.fetchone()[0]

            c.execute("SELECT language, COUNT(*) FROM telegram_users GROUP BY language")
            users_by_lang = {r[0]: r[1] for r in c.fetchall()}

            c.execute("SELECT COUNT(*) FROM user_sessions WHERE status = 'COMPLETED'")
            completed_sessions = c.fetchone()[0]

            c.execute("SELECT COUNT(*), SUM(passed) FROM exam_results")
            exam_row = c.fetchone()
            total_exams = exam_row[0] or 0
            passed_exams = exam_row[1] or 0

            c.execute("SELECT COUNT(*) FROM canonical_questions")
            canon_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM canonical_translations")
            trans_count = c.fetchone()[0]

            return {
                "total_users": total_users,
                "users_by_language": users_by_lang,
                "completed_sessions": completed_sessions,
                "total_exams": total_exams,
                "passed_exams": passed_exams,
                "exam_pass_rate": round((passed_exams / total_exams * 100), 1) if total_exams > 0 else 0.0,
                "canonical_questions": canon_count,
                "canonical_translations": trans_count,
                "status": "HEALTHY"
            }

    def log_admin_action(self, admin_id: int, action: str, details: Optional[str] = None):
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO admin_audit_logs (admin_id, action, details, performed_at) VALUES (?, ?, ?, ?)",
                      (admin_id, action, details, now_ts))
            conn.commit()

    def get_all_user_ids(self) -> List[int]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM telegram_users WHERE is_blocked = 0")
            return [r[0] for r in c.fetchall()]

    # --- Mini App Features: Bookmarks, Checklist, Streaks, History ---
    def toggle_bookmark(self, user_id: int, canonical_id: str) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?", (user_id, canonical_id))
            row = c.fetchone()
            if row:
                c.execute("DELETE FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?", (user_id, canonical_id))
                conn.commit()
                return False
            else:
                c.execute("INSERT INTO user_bookmarks (user_id, canonical_id, created_at) VALUES (?, ?, ?)",
                          (user_id, canonical_id, now_ts))
                conn.commit()
                return True

    def get_user_bookmarks(self, user_id: int) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT canonical_id FROM user_bookmarks WHERE user_id = ? ORDER BY id DESC", (user_id,))
            return [r[0] for r in c.fetchall()]

    def is_bookmarked(self, user_id: int, canonical_id: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM user_bookmarks WHERE user_id = ? AND canonical_id = ?", (user_id, canonical_id))
            return c.fetchone() is not None

    def get_checklist_status(self, user_id: int) -> Dict[str, bool]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT item_id, is_completed FROM practical_checklist WHERE user_id = ?", (user_id,))
            return {r[0]: bool(r[1]) for r in c.fetchall()}

    def toggle_checklist_item(self, user_id: int, item_id: str, is_completed: Optional[bool] = None) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT is_completed FROM practical_checklist WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            row = c.fetchone()
            if row is not None:
                new_val = (not bool(row[0])) if is_completed is None else bool(is_completed)
                c.execute("UPDATE practical_checklist SET is_completed = ?, updated_at = ? WHERE user_id = ? AND item_id = ?",
                          (1 if new_val else 0, now_ts, user_id, item_id))
            else:
                new_val = True if is_completed is None else bool(is_completed)
                c.execute("INSERT INTO practical_checklist (user_id, item_id, is_completed, updated_at) VALUES (?, ?, ?, ?)",
                          (user_id, item_id, 1 if new_val else 0, now_ts))
            conn.commit()
            return new_val

    def reset_checklist(self, user_id: int):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM practical_checklist WHERE user_id = ?", (user_id,))
            conn.commit()

    # --- Practical Modules Tracking ---
    def get_completed_modules(self, user_id: int) -> List[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT module_id FROM user_completed_modules WHERE user_id = ?", (user_id,))
            return [r[0] for r in c.fetchall()]

    def is_module_completed(self, user_id: int, module_id: str) -> bool:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM user_completed_modules WHERE user_id = ? AND module_id = ?", (user_id, module_id))
            return c.fetchone() is not None

    def toggle_completed_module(self, user_id: int, module_id: str) -> bool:
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM user_completed_modules WHERE user_id = ? AND module_id = ?", (user_id, module_id))
            row = c.fetchone()
            if row:
                c.execute("DELETE FROM user_completed_modules WHERE user_id = ? AND module_id = ?", (user_id, module_id))
                conn.commit()
                return False
            else:
                c.execute("INSERT INTO user_completed_modules (user_id, module_id, completed_at) VALUES (?, ?, ?)",
                          (user_id, module_id, now_ts))
                conn.commit()
                return True

    def record_practical_quiz_result(self, user_id: int, scenario_id: str, selected_option: int, is_correct: bool):
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO practical_quiz_results (user_id, scenario_id, selected_option, is_correct, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, scenario_id, selected_option, 1 if is_correct else 0, now_ts))
            conn.commit()

    def get_learning_streak(self, user_id: int) -> Dict[str, Any]:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT current_streak, last_active_date, daily_goal_questions, today_questions_count FROM learning_streak WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if not row:
                c.execute("""
                INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                VALUES (?, 0, ?, 20, 0, ?)
                """, (user_id, today_str, now_ts))
                conn.commit()
                return {
                    "current_streak": 0,
                    "last_active_date": today_str,
                    "daily_goal_questions": 20,
                    "today_questions_count": 0
                }
            
            streak = row[0]
            last_date = row[1]
            goal = row[2]
            today_count = row[3]

            # If last active date is earlier than today, reset today count
            if last_date != today_str:
                from datetime import timedelta
                yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                if last_date == yesterday_str:
                    pass  # Consecutive day
                else:
                    streak = 0  # Missed days, reset streak until user answers today
                today_count = 0
                c.execute("UPDATE learning_streak SET current_streak = ?, last_active_date = ?, today_questions_count = ?, updated_at = ? WHERE user_id = ?",
                          (streak, today_str, 0, now_ts, user_id))
                conn.commit()

            return {
                "current_streak": streak,
                "last_active_date": today_str,
                "daily_goal_questions": goal,
                "today_questions_count": today_count
            }

    def increment_streak_progress(self, user_id: int, count: int = 1) -> Dict[str, Any]:
        info = self.get_learning_streak(user_id)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        now_ts = datetime.utcnow().isoformat()
        new_today = info["today_questions_count"] + count
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE learning_streak SET today_questions_count = ?, last_active_date = ?, updated_at = ? WHERE user_id = ?",
                      (new_today, today_str, now_ts, user_id))
            conn.commit()
        info["today_questions_count"] = new_today
        return info

    def get_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT session_id, total_questions, correct_count, incorrect_count, percentage, passed, time_taken_seconds, created_at, COALESCE(unanswered_count, 0) as unanswered_count
            FROM exam_results
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """, (user_id, limit))
            res = []
            for r in c.fetchall():
                res.append({
                    "session_id": r["session_id"],
                    "total_questions": r["total_questions"],
                    "correct_count": r["correct_count"],
                    "incorrect_count": r["incorrect_count"],
                    "unanswered_count": r["unanswered_count"],
                    "percentage": r["percentage"],
                    "passed": bool(r["passed"]),
                    "time_taken_seconds": r["time_taken_seconds"],
                    "created_at": r["created_at"]
                })
            return res

    # --- RULLY 2.0: Daily Goal, Ticket Mastery, Session Review & Adaptive Analytics ---
    def set_daily_goal(self, user_id: int, goal_questions: int) -> int:
        goal = max(5, min(100, int(goal_questions)))
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
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
                    VALUES (?, 1, ?, ?, 0, ?)
                    """,
                    (user_id, today_str, goal, now_ts),
                )
            conn.commit()
        return goal

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
            self._ensure_ticket_progress_table(conn)
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
            self._ensure_ticket_progress_table(conn)
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
            res: Dict[int, Dict[str, Any]] = {}
            for r in c.fetchall():
                res[int(r["ticket_number"])] = {
                    "ticket_number": int(r["ticket_number"]),
                    "total_questions": int(r["total_questions"]),
                    "best_correct": int(r["best_correct"]),
                    "best_percentage": float(r["best_percentage"]),
                    "attempts_count": int(r["attempts_count"]),
                    "is_passed": bool(r["is_passed"]),
                    "last_session_id": r["last_session_id"],
                    "last_attempted_at": r["last_attempted_at"],
                }
            return res

    def get_solved_correct_ids(self, user_id: int) -> Set[str]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT DISTINCT sa.canonical_id
                FROM session_answers sa
                JOIN user_sessions us ON sa.session_id = us.session_id
                WHERE us.user_id = ? AND sa.is_correct = 1
                """,
                (user_id,),
            )
            return {r["canonical_id"] for r in c.fetchall()}

    def get_session_review(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session or session.get("user_id") != user_id:
            return None
        answers = self.get_session_answers(session_id)
        bookmarks = set(self.get_user_bookmarks(user_id))
        return {
            "session": session,
            "answers": answers,
            "bookmarks": bookmarks,
        }

    def get_learning_analytics(
        self,
        user_id: int,
        categories: List[Dict[str, Any]],
        engine_total_questions: int = 1327,
    ) -> Dict[str, Any]:
        """
        Computes per-category mastery, SM-2 spaced repetition summary, weak/strong topic rankings,
        milestones, and a real-time Smart Next Action recommendation.
        """
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            self._ensure_ticket_progress_table(conn)
            self._ensure_srs_schema(conn)
            c = conn.cursor()
            c.execute(
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id,
                       COUNT(sa.id) AS total_attempts,
                       COALESCE(SUM(sa.is_correct), 0) AS correct_attempts,
                       COUNT(DISTINCT sa.canonical_id) AS unique_answered,
                       COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct
                FROM session_answers sa
                JOIN user_sessions us ON sa.session_id = us.session_id
                LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
                WHERE us.user_id = ?
                GROUP BY COALESCE(cq.category_id, 0)
                """,
                (user_id,),
            )
            cat_perf = {
                int(r["category_id"]): {
                    "total_attempts": int(r["total_attempts"] or 0),
                    "correct_attempts": int(r["correct_attempts"] or 0),
                    "unique_answered": int(r["unique_answered"] or 0),
                    "unique_correct": int(r["unique_correct"] or 0),
                }
                for r in c.fetchall()
            }

            c.execute(
                """
                SELECT COALESCE(cq.category_id, 0) AS category_id,
                       COUNT(*) AS active_mistakes
                FROM user_mistakes um
                LEFT JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
                WHERE um.user_id = ? AND um.is_resolved = 0
                GROUP BY COALESCE(cq.category_id, 0)
                """,
                (user_id,),
            )
            cat_mistakes = {int(r["category_id"]): int(r["active_mistakes"] or 0) for r in c.fetchall()}

            c.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
                    (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
                    (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS active_mistakes,
                    (SELECT COALESCE(SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS resolved_mistakes,
                    (SELECT COALESCE(current_streak, 1) FROM learning_streak WHERE user_id = ?) AS current_streak,
                    (SELECT COUNT(*) FROM user_completed_modules WHERE user_id = ?) AS completed_modules,
                    (SELECT COUNT(*) FROM user_ticket_progress WHERE user_id = ? AND is_passed = 1) AS passed_tickets
                """,
                tuple([user_id] * 7),
            )
            summary_row = dict(c.fetchone() or {})
            srs_agg = self._query_srs_aggregate(conn, user_id, now_iso=now_ts)

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

        total_exams = int(summary_row.get("total_exams") or 0)
        passed_exams = int(summary_row.get("passed_exams") or 0)
        active_mistakes = int(summary_row.get("active_mistakes") or 0)
        resolved_mistakes = int(summary_row.get("resolved_mistakes") or 0)
        current_streak = int(summary_row.get("current_streak") or 1)
        completed_modules = int(summary_row.get("completed_modules") or 0)
        passed_tickets = int(summary_row.get("passed_tickets") or 0)
        srs_due_now = int(srs_agg["due_now_count"])
        srs_mastered = int(srs_agg["mastered_count"])

        # Smart Next Action Recommendation Engine (SM-2 integrated)
        if total_unique_answered < 10 and srs_due_now < 5:
            recommendation = {
                "kind": "adaptive_starter",
                "target_type": "ADAPTIVE",
                "target_id": None,
                "metric": total_unique_answered,
            }
        elif srs_due_now >= 5:
            recommendation = {
                "kind": "srs_review",
                "target_type": "SRS",
                "target_id": None,
                "metric": srs_due_now,
            }
        elif active_mistakes >= 5:
            recommendation = {
                "kind": "mistake_drill",
                "target_type": "MISTAKES",
                "target_id": None,
                "metric": active_mistakes,
            }
        elif srs_due_now >= 1:
            recommendation = {
                "kind": "srs_review",
                "target_type": "SRS",
                "target_id": None,
                "metric": srs_due_now,
            }
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
            recommendation = {
                "kind": "official_exam",
                "target_type": "EXAM",
                "target_id": None,
                "metric": total_exams,
            }
        else:
            recommendation = {
                "kind": "adaptive_mastery",
                "target_type": "ADAPTIVE",
                "target_id": None,
                "metric": round((total_unique_correct / max(1, engine_total_questions)) * 100.0, 1),
            }

        milestones = [
            {"id": "first_steps", "unlocked": total_unique_answered >= 10, "progress": min(10, total_unique_answered), "target": 10},
            {"id": "streak_3", "unlocked": current_streak >= 3, "progress": min(3, current_streak), "target": 3},
            {"id": "exam_passer", "unlocked": passed_exams >= 1, "progress": min(1, passed_exams), "target": 1},
            {"id": "mistake_slayer", "unlocked": resolved_mistakes >= 5, "progress": min(5, resolved_mistakes), "target": 5},
            {"id": "ticket_finisher", "unlocked": passed_tickets >= 5, "progress": min(5, passed_tickets), "target": 5},
            {"id": "avtodrom_pro", "unlocked": completed_modules >= 5, "progress": min(5, completed_modules), "target": 5},
            {"id": "memory_master", "unlocked": srs_mastered >= 25, "progress": min(25, srs_mastered), "target": 25},
        ]

        return {
            "overall_coverage_pct": round((total_unique_answered / max(1, engine_total_questions)) * 100.0, 1),
            "overall_mastery_pct": round((total_unique_correct / max(1, engine_total_questions)) * 100.0, 1),
            "unique_answered": total_unique_answered,
            "unique_correct": total_unique_correct,
            "total_bank_questions": engine_total_questions,
            "passed_tickets": passed_tickets,
            "completed_modules": completed_modules,
            "srs_summary": srs_agg,
            "category_mastery": category_mastery,
            "weak_categories": weak_categories,
            "strong_categories": strong_categories,
            "recommendation": recommendation,
            "milestones": milestones,
        }

    # --- Phase 5: SM-2 Spaced Repetition Repository Methods ---
    def record_srs_review(
        self,
        user_id: int,
        canonical_id: str,
        quality: int,
        now_dt: Optional[datetime] = None,
        recalibrate: bool = False,
    ) -> Dict[str, Any]:
        """
        Records a direct SM-2 spaced-repetition quality review (0..5) and keeps
        user_mistakes consistent inside a single atomic execute_batch().
        When recalibrate=True, recomputes cleanly from the pre-answer snapshot so
        a post-answer confidence button never double-increments repetitions.
        """
        ts_dt = now_dt or datetime.utcnow()
        now_ts = ts_dt.isoformat()
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
            prev = None
            has_snap = False
            if recalibrate:
                cached = _PRE_ANSWER_SRS_CACHE.get((user_id, canonical_id), default="__MISS__")
                if cached != "__MISS__":
                    prev = cached
                    has_snap = True
            if not has_snap:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT ease_factor, interval_days, repetitions, lapses
                    FROM user_question_srs
                    WHERE user_id = ? AND canonical_id = ?
                    """,
                    (user_id, canonical_id),
                )
                row = c.fetchone()
                prev = dict(row) if row else None
            next_srs = compute_next_sm2_state(prev, quality=quality, now=ts_dt)

            batch_stmts = [build_srs_upsert_stmt(user_id, canonical_id, next_srs)]
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
            execute_batch(conn, batch_stmts)
            return next_srs

    def get_srs_queue_summary(
        self,
        user_id: int,
        now_iso: Optional[str] = None,
        total_bank_questions: int = 1327,
        limit: int = 30,
    ) -> Dict[str, Any]:
        """
        Fetches overdue & due-now SM-2 review queue plus summary stats for "Aqlli Takrorlash".
        Orders most critical items first: lowest ease_factor, highest lapses, earliest next_review_at.
        """
        now_ts = now_iso or datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
            agg = self._query_srs_aggregate(conn, user_id, now_iso=now_ts)
            agg["total_bank_questions"] = int(total_bank_questions)
            c = conn.cursor()
            c.execute(
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
                """,
                (user_id, now_ts, max(1, int(limit))),
            )
            items: List[Dict[str, Any]] = []
            due_ids: List[str] = []
            for r in c.fetchall():
                d = dict(r)
                is_due = str(d["next_review_at"]) <= now_ts
                d["is_due"] = is_due
                d["ease_factor"] = round(float(d.get("ease_factor") or 2.5), 2)
                d["interval_days"] = int(d.get("interval_days") or 0)
                d["repetitions"] = int(d.get("repetitions") or 0)
                d["lapses"] = int(d.get("lapses") or 0)
                d["mastery_level"] = classify_srs_mastery(
                    d["repetitions"], d["interval_days"], d["ease_factor"], d["lapses"]
                )
                items.append(d)
                if is_due:
                    due_ids.append(d["canonical_id"])
            return {
                "summary": agg,
                "due_question_ids": due_ids,
                "items": items,
            }

    def get_question_srs_map(self, user_id: int, canonical_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Returns compact SM-2 state keyed by canonical_id for the requested question IDs."""
        clean_ids = [str(cid) for cid in canonical_ids if cid]
        if not clean_ids:
            return {}
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
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

    def get_ai_student_snapshot(self, user_id: int) -> Dict[str, Any]:
        with self._get_connection() as conn:
            self._ensure_srs_schema(conn)
            c = conn.cursor()
            c.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
                  (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
                  (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS active_mistakes,
                  (SELECT COUNT(DISTINCT sa.canonical_id) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ?) AS unique_answered
                """,
                (user_id, user_id, user_id, user_id),
            )
            r = dict(c.fetchone() or {})
            srs_agg = self._query_srs_aggregate(conn, user_id)
            return {
                "total_exams": int(r.get("total_exams") or 0),
                "passed_exams": int(r.get("passed_exams") or 0),
                "active_mistakes": int(r.get("active_mistakes") or 0),
                "unique_answered": int(r.get("unique_answered") or 0),
                "srs_tracked_total": int(srs_agg.get("tracked_count") or 0),
                "srs_due_now": int(srs_agg.get("due_now_count") or 0),
                "srs_mastered_count": int(srs_agg.get("mastered_count") or 0),
                "srs_learning_count": int(srs_agg.get("learning_count") or 0),
                "srs_avg_ease_factor": float(srs_agg.get("avg_ease_factor") or 2.5),
            }
