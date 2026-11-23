"""
Bot Database Repository & Data Access Layer for Telegram User Sessions,
Answers, Mistake Tracking, and Admin Analytics.
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple, Union
from src.db_adapter import get_db_connection, is_turso_enabled, execute_batch

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



def compute_driver_accuracy(
    total_answered: int,
    correct_answers: int,
    unique_questions: int = 0,
    unique_correct: int = 0,
    recent_total: int = 0,
    recent_correct: int = 0,
    categories_tested: int = 0,
    unresolved_mistakes: int = 0,
    return_details: bool = False
) -> Union[float, Dict[str, Any]]:
    """
    RULLY Multi-Criteria Driver Accuracy Engine (0.0 to 100.0%).
    
    Evaluates real driving knowledge precision against 5 intelligent criteria:
    1. Net Knowledge Accuracy above 25% Random Guessing Threshold (40% weight):
       Normalizes raw accuracy (R - 25.0) / 70.0 to filter out lucky random clicks.
    2. Recency Accuracy & Learning Dynamics (30% weight):
       Evaluates the most recent 40 questions to reward learning curve improvements.
    3. Distinct Question Mastery (20% weight):
       Unique correct questions / unique questions tested, preventing repetition cheating.
    4. Cross-Category Breadth (10% weight):
       Consistent accuracy across diverse YHQ traffic categories.
    5. Bayesian Statistical Confidence:
       Scales with sample size to prevent a 1-question beginner from getting a fake 100% accuracy.
    """
    if total_answered <= 0 or correct_answers <= 0:
        if return_details:
            return {
                "accuracy": 0.0,
                "raw_accuracy": 0.0,
                "net_knowledge_score": 0.0,
                "recent_accuracy": 0.0,
                "distinct_accuracy": 0.0,
                "confidence_factor": 0.0
            }
        return 0.0

    raw_acc = min(100.0, max(0.0, (correct_answers / total_answered) * 100.0))

    # 1. Net Knowledge Accuracy above 25% guessing baseline (40% weight)
    if raw_acc <= 25.0:
        net_acc = 0.0
    else:
        # Scale 25% -> 95%+ to 0.0 -> 100.0%
        net_acc = min(100.0, max(0.0, ((raw_acc - 25.0) / 70.0) * 100.0))

    # 2. Recent Accuracy (30% weight)
    if recent_total > 0:
        recent_acc = min(100.0, max(0.0, (recent_correct / recent_total) * 100.0))
    else:
        recent_acc = raw_acc

    # 3. Distinct Questions Accuracy (20% weight)
    if unique_questions > 0 and unique_correct > 0:
        distinct_acc = min(100.0, max(0.0, (unique_correct / unique_questions) * 100.0))
    else:
        distinct_acc = raw_acc

    # 4. Cross-Category Balance (10% weight)
    cat_count = categories_tested if categories_tested is not None else 0
    cat_factor = min(100.0, (cat_count / 12.0) * 100.0) if cat_count > 0 else distinct_acc

    # Raw multi-criteria composite
    composite = (
        0.40 * net_acc +
        0.30 * recent_acc +
        0.20 * distinct_acc +
        0.10 * cat_factor
    )

    # 5. Statistical Confidence Scaling
    if total_answered < 5:
        confidence = 0.40 + (total_answered / 10.0) * 0.20
    elif total_answered < 20:
        confidence = 0.60 + ((total_answered - 5) / 15.0) * 0.30
    elif total_answered < 35:
        confidence = 0.90 + ((total_answered - 20) / 15.0) * 0.10
    else:
        confidence = 1.0

    final_acc = composite * confidence

    # Safeguards:
    if raw_acc <= 25.0:
        final_acc = min(final_acc, 8.0)
    if unresolved_mistakes >= 15:
        final_acc = min(final_acc, 65.0)

    # For brand new users with 1-2 correct answers, cap at realistic 40%
    if total_answered <= 3 and correct_answers == total_answered:
        final_acc = min(final_acc, 40.0)

    final_acc = round(min(100.0, max(0.0, final_acc)), 1)

    if return_details:
        return {
            "accuracy": final_acc,
            "raw_accuracy": round(raw_acc, 1),
            "net_knowledge_score": round(net_acc, 1),
            "recent_accuracy": round(recent_acc, 1),
            "distinct_accuracy": round(distinct_acc, 1),
            "confidence_factor": round(confidence, 2)
        }
    return final_acc


def compute_driver_readiness(
    total_exams: int,
    passed_exams: int,
    pass_rate: float,
    total_answered: int,
    accuracy: float,
    unique_questions: int,
    unresolved_mistakes: int,
    categories_tested: int = None,
    resolved_mistakes: int = 0,
    current_streak: int = 0,
    avg_exam_time_seconds: float = 0.0,
    recent_pass_rate: float = None,
    return_details: bool = False
) -> Union[float, Dict[str, Any]]:
    """
    RULLY Intelligent 5-Pillar Exam Readiness Engine (0.0 to 100.0%).
    Calibrated specifically for the Uzbekistan State Driving Examination (DYHXX):
    - Requirements: 20 questions, 25 minutes, at least 18 correct (90%).
    - Max 2 mistakes permitted; 3 mistakes = IMMEDIATE FAILURE.

    5 Pillars:
    1. Exam Mastery & Consistency (30% weight):
       Requires passing multiple full exams under timer pressure to eliminate lucky draws.
    2. Knowledge Accuracy & Anti-Guessing (25% weight):
       Filters out 4-choice guessing baseline (35%). Scales from 35% (0 pts) to 95%+ (100 pts).
    3. Curriculum & Syllabus Coverage (25% weight):
       Broad exposure across the 1,295 question bank and 43 official categories.
    4. Mistake Bank Hygiene (10% weight):
       Unresolved mistakes are active failure risks; resolved mistakes award bonuses.
    5. Exam Pace & Practice Streak (10% weight):
       Pace management (200-1100s per exam) and daily active learning consistency.
    """
    if total_answered == 0 and total_exams == 0:
        details = {
            "readiness_score": 0.0,
            "grade": "NOT_READY",
            "pillars": {
                "exam_mastery": 0.0,
                "accuracy": 0.0,
                "coverage": 0.0,
                "mistake_hygiene": 0.0,
                "pace_and_streak": 0.0
            }
        }
        return details if return_details else 0.0

    # Pillar 1: Exam Passing Mastery & Consistency (30% weight)
    if passed_exams == 0:
        p_exam = 0.0
    else:
        rec_pass = recent_pass_rate if recent_pass_rate is not None else pass_rate
        consistency = min(1.0, passed_exams / 4.0)
        p_exam = min(100.0, (0.40 * pass_rate + 0.60 * rec_pass) * (0.35 + 0.65 * consistency))

    # Pillar 2: Knowledge Accuracy above 35% baseline (25% weight)
    if total_answered < 10 or accuracy <= 35.0:
        p_acc = 0.0
    else:
        p_acc = min(100.0, max(0.0, ((accuracy - 35.0) / 57.0) * 100.0))

    # Pillar 3: Curriculum / Syllabus Coverage (25% weight)
    if categories_tested is None or categories_tested <= 0:
        categories_tested = min(43, max(1, int(unique_questions / 8)))

    q_score = min(100.0, (unique_questions / 160.0) * 100.0)
    cat_score = min(100.0, (categories_tested / 20.0) * 100.0)
    p_cov = 0.60 * q_score + 0.40 * cat_score

    # Pillar 4: Mistake Bank Hygiene (10% weight)
    if total_answered < 5:
        p_mistakes = 50.0
    elif unresolved_mistakes == 0:
        p_mistakes = 100.0
    else:
        penalty = unresolved_mistakes * 5.0
        total_m = resolved_mistakes + unresolved_mistakes
        res_bonus = (resolved_mistakes / total_m * 20.0) if total_m > 0 else 0.0
        p_mistakes = max(0.0, min(100.0, 100.0 - penalty + res_bonus))

    # Pillar 5: Exam Pace & Practice Regularity (10% weight)
    s_score = min(100.0, max(30.0, current_streak * 25.0)) if current_streak > 0 else (100.0 if passed_exams >= 4 else (0.0 if total_exams > 0 and passed_exams == 0 else 50.0))
    if avg_exam_time_seconds <= 0:
        t_score = 100.0 if passed_exams >= 4 else (0.0 if total_exams > 0 and passed_exams == 0 else 50.0)
    elif 200 <= avg_exam_time_seconds <= 1100:
        t_score = 100.0
    elif avg_exam_time_seconds < 200:
        t_score = 30.0
    else:
        t_score = max(30.0, 100.0 - ((avg_exam_time_seconds - 1100) / 400.0) * 50.0)
    p_pace = 0.50 * s_score + 0.50 * t_score

    raw_score = (
        0.30 * p_exam +
        0.25 * p_acc +
        0.25 * p_cov +
        0.10 * p_mistakes +
        0.10 * p_pace
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
        final_score = min(raw_score, 68.0)
    else:
        final_score = raw_score

    if unresolved_mistakes >= 15 or accuracy <= 30.0:
        final_score = min(final_score, 8.0)
    elif unresolved_mistakes >= 10:
        final_score = min(final_score, 60.0)

    if total_answered < 60:
        final_score = min(final_score, 30.0)

    final_score = round(max(0.0, min(100.0, final_score)), 1)

    if final_score >= 85.0:
        grade = "EXCELLENT"
    elif final_score >= 75.0:
        grade = "EXAM_READY"
    elif final_score >= 45.0:
        grade = "IN_PROGRESS"
    else:
        grade = "NOT_READY"

    details = {
        "readiness_score": final_score,
        "grade": grade,
        "pillars": {
            "exam_mastery": round(p_exam, 1),
            "accuracy": round(p_acc, 1),
            "coverage": round(p_cov, 1),
            "mistake_hygiene": round(p_mistakes, 1),
            "pace_and_streak": round(p_pace, 1)
        }
    }
    return details if return_details else final_score


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
            c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON user_sessions(user_id, status);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_exam_results_user ON exam_results(user_id);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_answers_session ON session_answers(session_id);")

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

                return user_dict
            else:
                c.execute("""
                INSERT INTO telegram_users (user_id, username, first_name, last_name, language, is_language_selected, is_pro, subscription_tier, created_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 'free', ?, ?)
                """, (user_id, username, first_name, last_name, default_lang, now_ts, now_ts))
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
                    VALUES (?, 1, ?, 20, 0, ?)
                    """, (user_id, today_str, now_ts))
                    streak = {
                        "current_streak": 1,
                        "last_active_date": today_str,
                        "daily_goal_questions": 20,
                        "today_questions_count": 0
                    }
                else:
                    if last_date != today_str:
                        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                        if last_date != yesterday_str:
                            strk_val = 1
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
                VALUES (?, 1, ?, 20, 0, ?)
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
                    "current_streak": 1,
                    "last_active_date": today_str,
                    "daily_goal_questions": 20,
                    "today_questions_count": 0
                }

            # 2. Consolidated Telemetry, Readiness & Free Tier Metrics (1 single compound query)
            c.execute("""
            SELECT
              (SELECT COUNT(*) FROM exam_results WHERE user_id = ?) AS total_exams,
              (SELECT COALESCE(SUM(passed), 0) FROM exam_results WHERE user_id = ?) AS passed_exams,
              (SELECT COUNT(*) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ?) AS total_ans,
              (SELECT COALESCE(SUM(is_correct), 0) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ?) AS correct_ans,
              (SELECT COALESCE(SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS unresolved_mistakes,
              (SELECT COALESCE(SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END), 0) FROM user_mistakes WHERE user_id = ?) AS resolved_mistakes,
              (SELECT COUNT(DISTINCT sa.canonical_id) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ?) AS unique_qs,
              (SELECT COUNT(DISTINCT cq.category_id) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id WHERE us.user_id = ?) AS categories_tested,
              (SELECT COUNT(DISTINCT sa.canonical_id) FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ? AND sa.is_correct = 1) AS unique_correct,
              (SELECT COUNT(*) FROM user_sessions WHERE user_id = ? AND session_type = 'EXAM' AND status = 'IN_PROGRESS') AS active_in_progress_exams,
              (SELECT COUNT(*) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_count,
              (SELECT COALESCE(SUM(passed), 0) FROM (SELECT passed FROM exam_results WHERE user_id = ? ORDER BY id DESC LIMIT 5)) AS recent_exams_passed,
              (SELECT COALESCE(AVG(time_taken_seconds), 0) FROM (SELECT time_taken_seconds FROM exam_results WHERE user_id = ? AND time_taken_seconds > 0 ORDER BY id DESC LIMIT 5)) AS recent_avg_exam_time,
              (SELECT COUNT(*) FROM (SELECT sa.is_correct FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ? ORDER BY sa.id DESC LIMIT 40)) AS recent_ans_total,
              (SELECT COALESCE(SUM(is_correct), 0) FROM (SELECT sa.is_correct FROM session_answers sa JOIN user_sessions us ON sa.session_id = us.session_id WHERE us.user_id = ? ORDER BY sa.id DESC LIMIT 40)) AS recent_ans_correct
            """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id))
            stats_row = dict(c.fetchone() or {})

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
                return_details=True
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
                return_details=True
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
        session_id = f"SES-{int(time.time() * 1000)}-{user_id}"
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

    def process_session_answer(self, session_id: str, user_id: int, canonical_id: str,
                               selected_key: str, correct_key: str, is_correct: bool,
                               session_type: str = "EXAM") -> Dict[str, Any]:
        """
        Atomic execution for answer submission, mistake tracking, streak update,
        and exam termination check.
        Uses execute_batch() to group all write operations into a single Turso HTTP round-trip (<60ms).
        """
        now_ts = datetime.utcnow().isoformat()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            c = conn.cursor()

            # Guard: If EXAM session already reached 3 mistakes or was terminated, reject further answers
            if session_type == "EXAM":
                c.execute("SELECT status, incorrect_count FROM user_sessions WHERE session_id = ?", (session_id,))
                sess_row = c.fetchone()
                if sess_row and (sess_row["status"] in ("FAILED_MISTAKES", "COMPLETED", "TERMINATED") or (sess_row["incorrect_count"] or 0) >= 3):
                    return {
                        "is_new": False,
                        "streak": {"current_streak": 0, "today_questions_count": 0},
                        "is_exam_terminated": True
                    }
            else:
                c.execute("SELECT status, incorrect_count FROM user_sessions WHERE session_id = ?", (session_id,))
                sess_row = c.fetchone()

            # Check if this question was already answered to guarantee idempotency
            c.execute("SELECT is_correct FROM session_answers WHERE session_id = ? AND canonical_id = ?", (session_id, canonical_id))
            if c.fetchone() is not None:
                c.execute("SELECT current_streak, today_questions_count FROM learning_streak WHERE user_id = ?", (user_id,))
                st_row = c.fetchone()
                return {
                    "is_new": False,
                    "streak": {
                        "current_streak": st_row["current_streak"] if st_row else 1,
                        "today_questions_count": st_row["today_questions_count"] if st_row else 1
                    },
                    "is_exam_terminated": (sess_row["status"] == "FAILED_MISTAKES") if sess_row else False
                }

            # Fetch streak state to calculate updated streak
            c.execute("SELECT current_streak, today_questions_count, last_active_date FROM learning_streak WHERE user_id = ?", (user_id,))
            st_row = c.fetchone()
            if st_row:
                new_today = (st_row["today_questions_count"] or 0) + 1
                streak_info = {"current_streak": st_row["current_streak"], "today_questions_count": new_today}
                streak_stmt = (
                    "UPDATE learning_streak SET today_questions_count = ?, last_active_date = ?, updated_at = ? WHERE user_id = ?",
                    [new_today, today_str, now_ts, user_id]
                )
            else:
                streak_info = {"current_streak": 1, "today_questions_count": 1}
                streak_stmt = (
                    """
                    INSERT INTO learning_streak (user_id, current_streak, last_active_date, daily_goal_questions, today_questions_count, updated_at)
                    VALUES (?, 1, ?, 10, 1, ?)
                    """,
                    [user_id, today_str, now_ts]
                )

            # Determine exam termination condition
            curr_incorrect = (sess_row["incorrect_count"] or 0) if sess_row else 0
            new_incorrect = curr_incorrect + (0 if is_correct else 1)
            is_exam_terminated = (session_type == "EXAM" and new_incorrect >= 3)

            # Build batch containing all write operations
            batch_stmts = [
                ("""
                INSERT INTO session_answers (
                    session_id, canonical_id, selected_key, correct_key, is_correct, answered_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, [session_id, canonical_id, selected_key, correct_key, 1 if is_correct else 0, now_ts])
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

            if is_exam_terminated:
                batch_stmts.append((
                    "UPDATE user_sessions SET status = 'FAILED_MISTAKES', updated_at = ? WHERE session_id = ?",
                    [now_ts, session_id]
                ))

            execute_batch(conn, batch_stmts)

            return {
                "is_new": True,
                "streak": streak_info,
                "is_exam_terminated": is_exam_terminated
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
                              unanswered: int = 0, status: str = "COMPLETED") -> Optional[Dict[str, Any]]:
        """
        Batches exam result recording and session status update into a single round-trip HTTP request.
        """
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            batch_stmts = [
                ("""
                INSERT OR REPLACE INTO exam_results (
                    session_id, user_id, total_questions, correct_count, incorrect_count,
                    percentage, passed, time_taken_seconds, category_breakdown_json, created_at,
                    unanswered_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    session_id, user_id, total_q, correct, incorrect, pct,
                    1 if passed else 0, time_spent, json.dumps(category_breakdown), now_ts,
                    unanswered
                ]),
                ("UPDATE user_sessions SET status = ?, updated_at = ? WHERE session_id = ?", [status, now_ts, session_id])
            ]
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

            # Active & resolved mistakes count
            c.execute("""
            SELECT 
                SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END)
            FROM user_mistakes WHERE user_id = ?
            """, (user_id,))
            m_row = c.fetchone()
            mistakes_cnt = (m_row[0] or 0) if m_row else 0
            resolved_cnt = (m_row[1] or 0) if m_row else 0

            # Unique canonical questions tested & categories tested
            c.execute("""
            SELECT 
                COUNT(DISTINCT sa.canonical_id),
                COUNT(DISTINCT cq.category_id)
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
            WHERE us.user_id = ?
            """, (user_id,))
            u_row = c.fetchone()
            unique_qs = (u_row[0] or 0) if u_row else 0
            categories_tested = (u_row[1] or 0) if u_row else 0

            # Learning streak
            c.execute("SELECT current_streak FROM learning_streak WHERE user_id = ?", (user_id,))
            st_row = c.fetchone()
            current_streak = st_row[0] if st_row else 0

            # Recent exam history (last 5)
            c.execute("""
            SELECT passed, time_taken_seconds
            FROM exam_results
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
            """, (user_id,))
            recent_exams = c.fetchall()
            if recent_exams:
                recent_pass_rate = round(sum(r[0] for r in recent_exams) / len(recent_exams) * 100.0, 1)
                valid_times = [r[1] for r in recent_exams if r[1] and r[1] > 0]
                avg_exam_time = sum(valid_times) / len(valid_times) if valid_times else 0.0
            else:
                recent_pass_rate = None
                avg_exam_time = 0.0

            # Unique questions answered correctly
            c.execute("""
            SELECT COUNT(DISTINCT sa.canonical_id)
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            WHERE us.user_id = ? AND sa.is_correct = 1
            """, (user_id,))
            uc_row = c.fetchone()
            unique_correct = (uc_row[0] or 0) if uc_row else 0

            # Recent answers history (last 40 answers)
            c.execute("""
            SELECT sa.is_correct
            FROM session_answers sa
            JOIN user_sessions us ON sa.session_id = us.session_id
            WHERE us.user_id = ?
            ORDER BY sa.id DESC
            LIMIT 40
            """, (user_id,))
            recent_ans_rows = c.fetchall()
            recent_ans_total = len(recent_ans_rows)
            recent_ans_correct = sum(r[0] for r in recent_ans_rows if r[0] == 1)

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
                return_details=True
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
                return_details=True
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
                "readiness_pillars": readiness_info["pillars"]
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
