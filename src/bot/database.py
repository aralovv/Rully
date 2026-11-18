"""
Bot Database Repository & Data Access Layer for Telegram User Sessions,
Answers, Mistake Tracking, and Admin Analytics.
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from src.db_adapter import get_db_connection, is_turso_enabled

# --- Subscription Plans Specification ---
SUBSCRIPTION_PLANS = {
    "pro_14": {
        "id": "pro_14",
        "name": "14 kunlik PRO (2 hafta)",
        "duration_days": 14,
        "price_uzs": 14000,
        "price_formatted": "14 000 so‘m"
    },
    "pro_30": {
        "id": "pro_30",
        "name": "30 kunlik PRO (1 oy)",
        "duration_days": 30,
        "price_uzs": 25000,
        "price_formatted": "25 000 so‘m"
    }
}


def compute_driver_readiness(
    total_exams: int,
    passed_exams: int,
    pass_rate: float,
    total_answered: int,
    accuracy: float,
    unique_questions: int,
    unresolved_mistakes: int
) -> float:
    """
    Intelligent Multi-Pillar Exam Readiness Index (0.0 to 100.0%).
    Calibrated specifically for the Uzbekistan State Driving Examination (DYHXX):
    - Real requirements: 20 questions, 25 minutes, at least 18 correct (90%).
    - Max 2 mistakes permitted; 3 mistakes = IMMEDIATE FAILURE.

    Pillars:
    1. Official State Exam Mastery & Consistency (35% weight):
       Requires passing multiple full exams under timer pressure to eliminate lucky draws.
    2. Knowledge Accuracy (25% weight):
       Filters out 4-choice guessing baseline (35%). Scales from 35% (0 pts) to 92%+ (100 pts).
    3. Syllabus Coverage (20% weight):
       Broad exposure to question bank (benchmark: at least 160 unique questions).
    4. Mistake Bank Hygiene (20% weight):
       Unresolved mistakes are active failure points. Zero unresolved mistakes awards 100 pts,
       while each uncorrected mistake subtracts 5 pts.

    Statistical Confidence & Safeguard Gates:
    - Confidence factor: scales with sqrt(total_answered / 100).
    - 0 passed exams: Hard cap at 15.0% (never conquered real exam pressure).
    - 1 passed exam: Hard cap at 45.0% (single pass may be a lucky draw).
    - 2 passed exams: Hard cap at 70.0%.
    - >= 10 unresolved mistakes: Hard cap at 60.0% (fatal risk on exam).
    - < 60 total questions answered: Hard cap at 30.0% (insufficient empirical sample).
    """
    if total_answered == 0 and total_exams == 0:
        return 0.0

    # Pillar 1: Exam Passing Mastery & Consistency (35% weight)
    if passed_exams == 0:
        pillar_exam = 0.0
    else:
        # Consistency factor: 1 exam = 0.2, 3 exams = 0.6, 5+ exams = 1.0
        consistency = min(1.0, passed_exams / 5.0)
        pillar_exam = min(100.0, pass_rate * (0.40 + 0.60 * consistency))

    # Pillar 2: Knowledge Accuracy above 35% baseline (25% weight)
    if total_answered < 10 or accuracy <= 35.0:
        pillar_accuracy = 0.0
    else:
        # 35% accuracy yields 0 pts; 92% yields 100 pts
        pillar_accuracy = min(100.0, max(0.0, ((accuracy - 35.0) / 57.0) * 100.0))

    # Pillar 3: Curriculum / Syllabus Coverage (20% weight)
    pillar_coverage = min(100.0, (unique_questions / 160.0) * 100.0)

    # Pillar 4: Mistake Bank Health (20% weight)
    if total_answered < 5:
        pillar_mistakes = 0.0
    elif unresolved_mistakes == 0:
        pillar_mistakes = 100.0
    else:
        pillar_mistakes = max(0.0, 100.0 - (unresolved_mistakes * 5.0))

    raw_score = (
        (0.35 * pillar_exam) +
        (0.25 * pillar_accuracy) +
        (0.20 * pillar_coverage) +
        (0.20 * pillar_mistakes)
    )

    # Statistical Confidence Multiplier for low volume (< 100 questions)
    if total_answered < 100:
        conf_multiplier = min(1.0, max(0.2, (total_answered / 100.0) ** 0.5))
        raw_score = raw_score * conf_multiplier

    # Intelligent Safeguard Gates
    if passed_exams == 0:
        final_score = min(raw_score, 15.0)
    elif passed_exams == 1:
        final_score = min(raw_score, 45.0)
    elif passed_exams == 2:
        final_score = min(raw_score, 70.0)
    else:
        final_score = raw_score

    if unresolved_mistakes >= 10:
        final_score = min(final_score, 60.0)

    if total_answered < 60:
        final_score = min(final_score, 30.0)

    return round(max(0.0, min(100.0, final_score)), 1)


class BotDatabase:
    def __init__(self, db_path: str = "master_database.sqlite"):
        self.db_path = db_path
        if not is_turso_enabled():
            self._init_bot_schema()

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

            # Performance indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_checklist_user ON practical_checklist(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_modules_user ON user_completed_modules(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_subs_user ON user_subscriptions(user_id);")

            conn.commit()

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
                c.execute("""
                UPDATE telegram_users
                SET username = ?, first_name = ?, last_name = ?, last_active_at = ?
                WHERE user_id = ?
                """, (username, first_name, last_name, now_ts, user_id))
                conn.commit()
                c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
                user_dict = dict(c.fetchone())
                user_dict["subscription"] = self.get_user_subscription(user_id)
                return user_dict
            else:
                c.execute("""
                INSERT INTO telegram_users (user_id, username, first_name, last_name, language, is_language_selected, is_pro, subscription_tier, created_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                """, (user_id, username, first_name, last_name, default_lang, now_ts, now_ts))
                conn.commit()
                c.execute("SELECT * FROM telegram_users WHERE user_id = ?", (user_id,))
                user_dict = dict(c.fetchone())
                user_dict["subscription"] = self.get_user_subscription(user_id)
                return user_dict

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
        session_id = f"SES-{int(time.time() * 1000)}-{user_id}"
        now_ts = datetime.utcnow().isoformat()
        start_t = time.time()
        deadline = (start_t + time_limit_seconds) if time_limit_seconds > 0 else None

        with self._get_connection() as conn:
            c = conn.cursor()
            # Abort any existing in-progress session for this user
            c.execute("UPDATE user_sessions SET status = 'ABORTED' WHERE user_id = ? AND status = 'IN_PROGRESS'", (user_id,))
            c.execute("""
            INSERT INTO user_sessions (
                session_id, user_id, session_type, category_id, language,
                total_questions, current_index, correct_count, incorrect_count,
                status, start_time, time_limit_seconds, deadline, question_ids_json,
                show_answer, show_explanation, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 'IN_PROGRESS', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, session_type, category_id, language,
                len(question_ids), start_t, time_limit_seconds, deadline,
                json.dumps(question_ids), 1 if show_answer else 0, 1 if show_explanation else 0,
                now_ts, now_ts
            ))
            conn.commit()

        return self.get_session(session_id)

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
                    session_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts))
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

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        with self._get_connection() as conn:
            c = conn.cursor()
            # Total exams taken
            c.execute("SELECT COUNT(*), SUM(passed) FROM exam_results WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            total_exams = row[0] or 0
            passed_exams = row[1] or 0

            # Total questions answered
            c.execute("""
            SELECT COUNT(*), SUM(is_correct)
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            WHERE us.user_id = ?
            """, (user_id,))
            ans_row = c.fetchone()
            total_ans = ans_row[0] or 0
            correct_ans = ans_row[1] or 0

            # Active mistakes count
            c.execute("SELECT COUNT(*) FROM user_mistakes WHERE user_id = ? AND is_resolved = 0", (user_id,))
            mistakes_cnt = c.fetchone()[0]

            # Unique canonical questions tested
            c.execute("""
            SELECT COUNT(DISTINCT sa.canonical_id)
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            WHERE us.user_id = ?
            """, (user_id,))
            unique_qs = c.fetchone()[0] or 0

            pass_rate = round((passed_exams / total_exams * 100), 1) if total_exams > 0 else 0.0
            accuracy = round((correct_ans / total_ans * 100), 1) if total_ans > 0 else 0.0

            readiness = compute_driver_readiness(
                total_exams=total_exams,
                passed_exams=passed_exams,
                pass_rate=pass_rate,
                total_answered=total_ans,
                accuracy=accuracy,
                unique_questions=unique_qs,
                unresolved_mistakes=mistakes_cnt
            )

            return {
                "total_exams": total_exams,
                "passed_exams": passed_exams,
                "pass_rate": pass_rate,
                "total_questions_answered": total_ans,
                "correct_answers": correct_ans,
                "accuracy": accuracy,
                "unresolved_mistakes": mistakes_cnt,
                "unique_questions_tested": unique_qs,
                "readiness_score": readiness
            }

    # --- Admin Analytics ---
    def get_admin_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM telegram_users")
            total_users = c.fetchone()[0]

            c.execute("SELECT language, COUNT(*) FROM telegram_users GROUP BY language")
            users_by_lang = dict(c.fetchall())

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
                VALUES (?, 1, ?, 20, 0, ?)
                """, (user_id, today_str, now_ts))
                conn.commit()
                return {
                    "current_streak": 1,
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
                    streak = 1  # Missed days, reset streak
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
