"""
Bot Database Facade & Consolidated Repository Entrypoint (`BotDatabase`).
Delegates domain queries to modular repositories under `src/db/repos/` while
preserving backward-compatible signatures across FastAPI routes, Telegram bot, and tests.
"""

import os
import sqlite3
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.db.repos import (
    AnalyticsRepo,
    DEFAULT_SUBSCRIPTION_PLANS,
    EditorialRepo,
    ExamsRepo,
    PaymentsRepo,
    SessionsRepo,
    SrsRepo,
    UsersRepo,
)
from src.db.scoring import compute_driver_accuracy, compute_driver_readiness
from src.db_adapter import execute_batch, get_db_connection, is_turso_enabled

SUBSCRIPTION_PLANS = DEFAULT_SUBSCRIPTION_PLANS


class BotDatabase:
    """Backward-compatible facade composing all 7 domain repositories."""

    _local_schema_ready_paths: Set[str] = set()
    _schema_lock: Lock = Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "master_database.sqlite")
        if not is_turso_enabled():
            self._init_local_dev_schema()

        self.users = UsersRepo(conn_factory=self._get_connection, db_path=self.db_path)
        self.payments = PaymentsRepo(conn_factory=self._get_connection, db_path=self.db_path)
        self.srs = SrsRepo(conn_factory=self._get_connection, db_path=self.db_path)
        self.exams = ExamsRepo(conn_factory=self._get_connection, db_path=self.db_path)
        self.sessions = SessionsRepo(conn_factory=self._get_connection, db_path=self.db_path)
        self.analytics = AnalyticsRepo(conn_factory=self._get_connection, db_path=self.db_path, srs_repo=self.srs)
        self.editorial = EditorialRepo(conn_factory=self._get_connection, db_path=self.db_path)

    def _get_connection(self):
        return get_db_connection(self.db_path)

    def _init_local_dev_schema(self) -> None:
        """Initializes local SQLite schema once per DB path for offline dev/test fixtures."""
        key = os.path.abspath(self.db_path)
        with BotDatabase._schema_lock:
            if key in BotDatabase._local_schema_ready_paths:
                return

        with self._get_connection() as conn:
            c = conn.cursor()
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS telegram_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT NOT NULL DEFAULT 'uz_latn',
                    is_language_selected INTEGER NOT NULL DEFAULT 0,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    is_pro INTEGER NOT NULL DEFAULT 0,
                    subscription_tier TEXT NOT NULL DEFAULT 'free',
                    subscription_expires_at TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL
                );
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
                CREATE TABLE IF NOT EXISTS admin_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    performed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    canonical_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
                    UNIQUE(user_id, canonical_id)
                );
                CREATE TABLE IF NOT EXISTS learning_streak (
                    user_id INTEGER PRIMARY KEY,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    last_active_date TEXT NOT NULL,
                    daily_goal_questions INTEGER NOT NULL DEFAULT 20,
                    today_questions_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS user_completed_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    module_id TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, module_id)
                );
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
                    prev_state_json TEXT DEFAULT NULL,
                    PRIMARY KEY (user_id, canonical_id),
                    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS ai_usage_limits (
                    user_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, usage_date)
                );
                CREATE TABLE IF NOT EXISTS user_activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    event_data TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
                );
                CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);
                CREATE INDEX IF NOT EXISTS idx_modules_user ON user_completed_modules(user_id);
                CREATE INDEX IF NOT EXISTS idx_subs_user ON user_subscriptions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON user_sessions(user_id, status);
                CREATE INDEX IF NOT EXISTS idx_exam_results_user ON exam_results(user_id);
                CREATE INDEX IF NOT EXISTS idx_answers_session ON session_answers(session_id);
                CREATE INDEX IF NOT EXISTS idx_ticket_progress_user ON user_ticket_progress(user_id);
                CREATE INDEX IF NOT EXISTS idx_srs_user_due ON user_question_srs(user_id, next_review_at);
                CREATE INDEX IF NOT EXISTS idx_srs_user_reps ON user_question_srs(user_id, repetitions, lapses);
                """
            )
            # Reconcile legacy local SQLite files missing Phase 1/4 columns idempotently
            for alter_stmt in (
                "ALTER TABLE user_sessions ADD COLUMN show_answer INTEGER NOT NULL DEFAULT 1",
                "ALTER TABLE user_sessions ADD COLUMN show_explanation INTEGER NOT NULL DEFAULT 1",
                "ALTER TABLE exam_results ADD COLUMN unanswered_count INTEGER DEFAULT 0",
                "ALTER TABLE telegram_users ADD COLUMN is_language_selected INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE telegram_users ADD COLUMN is_pro INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE telegram_users ADD COLUMN subscription_tier TEXT NOT NULL DEFAULT 'free'",
                "ALTER TABLE telegram_users ADD COLUMN subscription_expires_at TEXT DEFAULT NULL",
                "ALTER TABLE session_answers ADD COLUMN user_id INTEGER DEFAULT NULL",
                "ALTER TABLE user_question_srs ADD COLUMN prev_state_json TEXT DEFAULT NULL",
            ):
                try:
                    c.execute(alter_stmt)
                except sqlite3.OperationalError:
                    pass
            for idx_stmt in (
                "CREATE INDEX IF NOT EXISTS idx_session_answers_user_recent ON session_answers(user_id, id DESC)",
                "CREATE INDEX IF NOT EXISTS idx_session_answers_user_canon ON session_answers(user_id, canonical_id, is_correct)",
                "CREATE INDEX IF NOT EXISTS idx_session_answers_user_answered ON session_answers(user_id, is_correct, answered_at)",
            ):
                try:
                    c.execute(idx_stmt)
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        with BotDatabase._schema_lock:
            BotDatabase._local_schema_ready_paths.add(key)

    def _ensure_srs_schema(self, conn: Any) -> None:
        """Backward-compatible helper for explicit migration tests only (never called on hot paths)."""
        from src.db.migrations_v2 import apply_phase5_migrations, apply_phase4_migrations
        apply_phase5_migrations(conn)
        apply_phase4_migrations(conn)

    def _ensure_ticket_progress_table(self, conn: Any) -> None:
        """Backward-compatible helper for explicit migration tests only (never called on hot paths)."""
        from src.db.migrations_v2 import apply_phase1_migrations
        apply_phase1_migrations(conn)

    # --- Users ---
    def get_or_create_user(self, user_id: int, username: Optional[str] = None,
                           first_name: Optional[str] = None, last_name: Optional[str] = None,
                           default_lang: str = "uz_latn") -> Dict[str, Any]:
        return self.users.get_or_create_user(user_id, username=username, first_name=first_name, last_name=last_name, default_lang=default_lang)

    def set_user_language(self, user_id: int, language: str) -> bool:
        return self.users.set_user_language(user_id, language)

    def has_user_selected_language(self, user_id: int) -> bool:
        return self.users.has_user_selected_language(user_id)

    def get_user_language(self, user_id: int) -> str:
        return self.users.get_user_language(user_id)

    def get_all_user_ids(self) -> List[int]:
        return self.users.get_all_user_ids()

    # --- Subscriptions & Monetization ---
    def get_user_subscription(self, user_id: int) -> Dict[str, Any]:
        return self.payments.get_user_subscription(user_id)

    def get_user_exam_count(self, user_id: int) -> int:
        return self.payments.get_user_exam_count(user_id)

    def get_user_free_tier_status(self, user_id: int, subscription: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.payments.get_user_free_tier_status(user_id, subscription=subscription)

    def activate_subscription(self, user_id: int, plan_id: str) -> Dict[str, Any]:
        return self.payments.activate_subscription(user_id, plan_id)

    # --- Sessions & Quiz ---
    def create_session(self, user_id: int, session_type: str, language: str,
                       question_ids: List[str], time_limit_seconds: int = 0,
                       category_id: Optional[int] = None, show_answer: bool = True,
                       show_explanation: bool = True, preloaded_bookmarks: Optional[Set[str]] = None,
                       log_event_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.sessions.create_session(
            user_id=user_id,
            session_type=session_type,
            language=language,
            question_ids=question_ids,
            time_limit_seconds=time_limit_seconds,
            category_id=category_id,
            show_answer=show_answer,
            show_explanation=show_explanation,
            preloaded_bookmarks=preloaded_bookmarks,
            log_event_data=log_event_data,
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get_session(session_id)

    def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.sessions.get_active_session(user_id)

    def save_answer(self, session_id: str, canonical_id: str, selected_key: str, correct_key: str, is_correct: bool) -> bool:
        return self.sessions.save_answer(session_id, canonical_id, selected_key, correct_key, is_correct)

    def process_session_answer(self, session_id: str, user_id: int, canonical_id: str,
                               selected_key: str, correct_key: str, is_correct: bool,
                               session_type: str = "EXAM", response_time_ms: Optional[int] = None,
                               quality: Optional[int] = None) -> Dict[str, Any]:
        return self.sessions.process_session_answer(
            session_id=session_id,
            user_id=user_id,
            canonical_id=canonical_id,
            selected_key=selected_key,
            correct_key=correct_key,
            is_correct=is_correct,
            session_type=session_type,
            response_time_ms=response_time_ms,
            quality=quality,
        )

    def submit_session_answer_verified(self, session_id: str, user_id: int, canonical_id: str,
                                       selected_key: str, answer_checker: Callable[[str, str, str], Any],
                                       requested_lang: Optional[str] = None,
                                       response_time_ms: Optional[int] = None,
                                       quality: Optional[int] = None) -> Dict[str, Any]:
        return self.sessions.submit_session_answer_verified(
            session_id=session_id,
            user_id=user_id,
            canonical_id=canonical_id,
            selected_key=selected_key,
            answer_checker=answer_checker,
            requested_lang=requested_lang,
            response_time_ms=response_time_ms,
            quality=quality,
        )

    def get_session_answers(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        return self.sessions.get_session_answers(session_id)

    def advance_session(self, session_id: str) -> int:
        return self.sessions.advance_session(session_id)

    def finish_session(self, session_id: str, status: str = "COMPLETED") -> Optional[Dict[str, Any]]:
        return self.sessions.finish_session(session_id, status=status)

    def upsert_ticket_progress(self, user_id: int, ticket_number: int, total_questions: int,
                               correct_count: int, percentage: float, passed: bool, session_id: str) -> None:
        return self.sessions.upsert_ticket_progress(user_id, ticket_number, total_questions, correct_count, percentage, passed, session_id)

    def get_ticket_progress_map(self, user_id: int) -> Dict[int, Dict[str, Any]]:
        return self.sessions.get_ticket_progress_map(user_id)

    def get_solved_correct_ids(self, user_id: int) -> Set[str]:
        return self.sessions.get_solved_correct_ids(user_id)

    def get_session_review(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        return self.sessions.get_session_review(session_id, user_id)

    def get_session_finish_bundle(self, session_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        return self.sessions.get_session_finish_bundle(session_id, user_id)

    # --- Exams, Mistakes & Bookmarks ---
    def record_mistake(self, user_id: int, canonical_id: str) -> None:
        return self.exams.record_mistake(user_id, canonical_id)

    def resolve_mistake(self, user_id: int, canonical_id: str) -> None:
        return self.exams.resolve_mistake(user_id, canonical_id)

    def get_user_mistakes(self, user_id: int, limit: int = 20) -> List[str]:
        return self.exams.get_user_mistakes(user_id, limit=limit)

    def get_user_mistakes_count(self, user_id: int) -> int:
        return self.exams.get_user_mistakes_count(user_id)

    def save_exam_result(self, session_id: str, user_id: int, total_q: int,
                         correct: int, incorrect: int, pct: float, passed: bool,
                         time_spent: float, category_breakdown: Dict[str, Any], unanswered: int = 0) -> None:
        return self.exams.save_exam_result(session_id, user_id, total_q, correct, incorrect, pct, passed, time_spent, category_breakdown, unanswered=unanswered)

    def finalize_exam_session(self, session_id: str, user_id: int, total_q: int,
                              correct: int, incorrect: int, pct: float, passed: bool,
                              time_spent: float, category_breakdown: Dict[str, Any],
                              unanswered: int = 0, status: str = "COMPLETED",
                              record_exam_result: bool = True,
                              ticket_number: Optional[int] = None) -> None:
        return self.exams.finalize_exam_session(
            session_id=session_id,
            user_id=user_id,
            total_q=total_q,
            correct=correct,
            incorrect=incorrect,
            pct=pct,
            passed=passed,
            time_spent=time_spent,
            category_breakdown=category_breakdown,
            unanswered=unanswered,
            status=status,
            record_exam_result=record_exam_result,
            ticket_number=ticket_number,
        )

    def get_user_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        return self.exams.get_user_exam_history(user_id, limit=limit)

    def get_exam_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        return self.exams.get_exam_history(user_id, limit=limit)

    def toggle_bookmark(self, user_id: int, canonical_id: str) -> bool:
        return self.exams.toggle_bookmark(user_id, canonical_id)

    def get_user_bookmarks(self, user_id: int) -> List[str]:
        return self.exams.get_user_bookmarks(user_id)

    def is_bookmarked(self, user_id: int, canonical_id: str) -> bool:
        return self.exams.is_bookmarked(user_id, canonical_id)

    # --- SRS ---
    def _query_srs_aggregate(self, conn: Any, user_id: int, now_iso: Optional[str] = None) -> Dict[str, Any]:
        return self.srs.query_srs_aggregate(conn, user_id, now_iso=now_iso)

    def record_srs_review(self, user_id: int, canonical_id: str, quality: int,
                          now_dt=None, recalibrate: bool = False) -> Dict[str, Any]:
        return self.srs.record_srs_review(user_id, canonical_id, quality, now_dt=now_dt, recalibrate=recalibrate)

    def get_srs_queue_summary(self, user_id: int, now_iso: Optional[str] = None,
                              total_bank_questions: int = 1327, limit: int = 30) -> Dict[str, Any]:
        return self.srs.get_srs_queue_summary(user_id, now_iso=now_iso, total_bank_questions=total_bank_questions, limit=limit)

    def get_question_srs_map(self, user_id: int, canonical_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        return self.srs.get_question_srs_map(user_id, canonical_ids)

    # --- Analytics & Boot ---
    def get_user_answered_count(self, user_id: int) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM session_answers WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            return int((row[0] if row else 0) or 0)

    def get_user_stats(self, user_id: int, engine_total_questions: int = 1327) -> Dict[str, Any]:
        return self.analytics.get_user_stats(user_id, engine_total_questions=engine_total_questions)

    def get_user_full_auth_bundle(self, user_id: int, username: Optional[str] = None,
                                  first_name: Optional[str] = None, last_name: Optional[str] = None,
                                  default_lang: str = "uz_latn",
                                  categories: Optional[List[Dict[str, Any]]] = None,
                                  engine_total_questions: int = 1327) -> Dict[str, Any]:
        return self.analytics.get_user_full_auth_bundle(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            default_lang=default_lang,
            categories=categories,
            engine_total_questions=engine_total_questions,
        )

    def get_learning_streak(self, user_id: int) -> Dict[str, Any]:
        return self.analytics.get_learning_streak(user_id)

    def increment_streak_progress(self, user_id: int, count: int = 1) -> Dict[str, Any]:
        return self.analytics.increment_streak_progress(user_id, count=count)

    def set_daily_goal(self, user_id: int, goal_questions: int) -> int:
        return self.analytics.set_daily_goal(user_id, goal_questions)

    def get_learning_analytics(self, user_id: int, categories: List[Dict[str, Any]],
                               engine_total_questions: int = 1327) -> Dict[str, Any]:
        return self.analytics.get_learning_analytics(user_id, categories, engine_total_questions=engine_total_questions)

    def get_ai_student_snapshot(self, user_id: int) -> Dict[str, Any]:
        return self.analytics.get_ai_student_snapshot(user_id)

    def get_admin_stats(self) -> Dict[str, Any]:
        return self.analytics.get_admin_stats()

    def log_admin_action(self, admin_id: int, action: str, details: Optional[str] = None) -> None:
        return self.analytics.log_admin_action(admin_id, action, details=details)

    # --- Practical Modules & Editorial ---
    def get_completed_modules(self, user_id: int) -> List[str]:
        return self.editorial.get_completed_modules(user_id)

    def is_module_completed(self, user_id: int, module_id: str) -> bool:
        return self.editorial.is_module_completed(user_id, module_id)

    def toggle_completed_module(self, user_id: int, module_id: str) -> bool:
        return self.editorial.toggle_completed_module(user_id, module_id)
