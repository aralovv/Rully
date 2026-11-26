"""
Avtotest Product Engine & Data Access Layer.
Provides high-level APIs for test practice, exam simulation, multilingual presentation,
and mistake review for Uzbekistan driving licence preparation platforms.
"""

import os
import sys
import sqlite3
import random
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from src.bot.category_localization import localize_category, localize_legal_reference
from src.db_adapter import get_db_connection, is_turso_enabled
from src.db.catalog_bundle import (
    DEFAULT_BUNDLE_PATH,
    get_db_catalog_revision,
    verify_and_load_canonical_bundle,
)

logger = logging.getLogger(__name__)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Default exam configuration matching Uzbekistan driving exam rules (VMQ 408 / TIM standards)
DEFAULT_EXAM_CONFIG = {
    "total_questions": 20,
    "time_limit_seconds": 25 * 60,  # 25 minutes
    "passing_score": 18,            # Maximum 2 mistakes allowed
    "shuffle_options": False        # Keep standard A, B, C, D order
}

SUPPORTED_LANGUAGES = {
    "uz_latn": "O'zbekcha (Lotin)",
    "uz_cyrl": "Ўзбекча (Кирилл)",
    "ru": "Русский"
}

@dataclass
class AnswerOption:
    option_key: str
    text: str
    sort_order: int

@dataclass
class QuestionItem:
    canonical_id: str
    category_id: Optional[int]
    category_name: str
    language: str
    question_text: str
    options: List[AnswerOption]
    has_image: bool
    image_path: Optional[str]
    explanation: Optional[str] = None
    legal_reference: Optional[str] = None
    correct_option_key: Optional[str] = None
    legal_verification_status: Optional[str] = None
    legal_chapter: Optional[str] = None
    legal_clause: Optional[str] = None
    legal_doc_title: Optional[str] = None

@dataclass
class QuestionFeedback:
    canonical_id: str
    submitted_key: str
    correct_key: str
    is_correct: bool
    explanation: Optional[str]
    legal_reference: Optional[str]
    legal_verification_status: Optional[str] = None
    legal_chapter: Optional[str] = None
    legal_clause: Optional[str] = None
    legal_doc_title: Optional[str] = None

@dataclass
class ExamSessionResult:
    session_id: str
    language: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    score_percentage: float
    passed: bool
    time_elapsed_seconds: float
    category_breakdown: Dict[str, Dict[str, int]]
    incorrect_question_ids: List[str]

class AvtotestProductEngine:
    REVISION_CHECK_TTL_SECONDS = 300.0

    def __init__(self, db_path: Optional[str] = None, bundle_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "master_database.sqlite")
        if bundle_path is not None:
            self.bundle_path: Optional[str] = bundle_path
        elif os.path.normpath(self.db_path) == os.path.normpath("master_database.sqlite"):
            self.bundle_path = os.getenv("CANONICAL_BUNDLE_PATH", DEFAULT_BUNDLE_PATH)
        else:
            # Explicit custom SQLite paths (e.g., isolated test DBs) bypass global bundle unless passed explicitly.
            self.bundle_path = None

        if not is_turso_enabled() and not os.path.exists(self.db_path) and not (
            self.bundle_path and os.path.exists(self.bundle_path)
        ):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        self._cache_lock = threading.RLock()
        self._cache_questions: Dict[str, Dict[str, Any]] = {}
        self._cache_categories: List[Dict[str, Any]] = []
        self._by_category: Dict[int, List[str]] = {}
        self._all_canonical_ids: List[str] = []
        self._cache_source: str = "unloaded"
        self._cache_revision: Optional[int] = None
        self._last_revision_check_at: float = 0.0
        self._preload_cache()

    def _get_connection(self):
        if os.path.exists(self.db_path) and not (is_turso_enabled() and os.path.normpath(self.db_path) == os.path.normpath("master_database.sqlite")):
            conn = sqlite3.connect(self.db_path, timeout=15.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        return get_db_connection(self.db_path)

    def _populate_from_bundle(self, bundle: Dict[str, Any], source_label: str = "bundle"):
        new_questions: Dict[str, Dict[str, Any]] = {}
        new_by_category: Dict[int, List[str]] = {}
        new_all_ids: List[str] = []

        for item in bundle.get("questions", []):
            cid = item["canonical_id"]
            cat = item.get("category") or {}
            cat_id_raw = cat.get("id")
            cat_id = cat_id_raw if cat_id_raw is not None else 0
            legal = item.get("legal") or {}
            img = item.get("image") or {}

            translations: Dict[str, Dict[str, Any]] = {}
            for lang_code, tr in (item.get("translations") or {}).items():
                translations[lang_code] = {
                    "question_text": tr.get("question_text", ""),
                    "explanation": tr.get("explanation"),
                }

            answers: List[Dict[str, Any]] = []
            for opt in (item.get("options") or []):
                text_map = opt.get("text") or {}
                answers.append({
                    "option_key": opt["key"],
                    "text_uz_latn": text_map.get("uz_latn", ""),
                    "text_uz_cyrl": text_map.get("uz_cyrl", ""),
                    "text_ru": text_map.get("ru", ""),
                    "sort_order": opt.get("sort_order", 0),
                })

            new_questions[cid] = {
                "canonical_id": cid,
                "category_id": cat_id_raw,
                "category_name": cat.get("name") or "",
                "has_image": bool(item.get("has_image")),
                "correct_option_key": item.get("correct_option_key"),
                "legal_reference": legal.get("reference"),
                "legal_verification_status": legal.get("legal_verification_status"),
                "legal_doc_title": legal.get("doc_title"),
                "legal_chapter": legal.get("chapter"),
                "legal_clause": legal.get("clause"),
                "image_local_path": img.get("path") if item.get("has_image") else None,
                "translations": translations,
                "answers": answers,
            }
            new_by_category.setdefault(cat_id, []).append(cid)
            new_all_ids.append(cid)

        new_categories = [
            {
                "category_id": c_item.get("category_id", 0),
                "category_name": c_item.get("category_name") or "",
                "question_count": c_item.get("question_count", 0),
            }
            for c_item in bundle.get("categories", [])
        ]

        self._cache_questions = new_questions
        self._cache_categories = new_categories
        self._by_category = new_by_category
        self._all_canonical_ids = new_all_ids
        self._cache_source = source_label
        self._cache_revision = int(bundle.get("db_catalog_revision", 0))
        self._last_revision_check_at = time.monotonic()

    def _preload_cache(self):
        """
        Loads canonical questions using SHA-256 verified bundle first when aligned with
        DB catalog_version, falling back cleanly to live SQL preload on bundle absence/drift.
        """
        with self._cache_lock:
            bundle = None
            bundle_err = None
            if self.bundle_path:
                bundle, bundle_err = verify_and_load_canonical_bundle(self.bundle_path)

            db_rev: Optional[int] = None
            conn = None
            try:
                conn = self._get_connection()
                db_rev = get_db_catalog_revision(conn)

                # Case A: Cryptographically verified bundle matches live catalog_version (0 heavy SQL transfer!)
                if bundle is not None and db_rev is not None and int(bundle.get("db_catalog_revision", -1)) == db_rev:
                    self._populate_from_bundle(bundle, source_label="bundle")
                    return

                # Case B: Missing, tampered, or stale bundle -> structured warning & automatic live SQL fallback
                if self.bundle_path:
                    reason = bundle_err or f"REVISION_DRIFT(bundle={bundle.get('db_catalog_revision')},db={db_rev})"
                    logger.warning("CATALOG_BUNDLE_STALE_FALLBACK: %s", reason)

                new_questions: Dict[str, Dict[str, Any]] = {}
                new_by_category: Dict[int, List[str]] = {}
                new_all_ids: List[str] = []

                c = conn.cursor()
                try:
                    c.execute("""
                    SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
                           cq.correct_option_key, cq.legal_reference,
                           cq.legal_verification_status, cq.legal_chapter, cq.legal_clause, cq.legal_doc_title,
                           im.local_path as image_local_path
                    FROM canonical_questions cq
                    LEFT JOIN images im ON cq.primary_image_id = im.id
                    ORDER BY cq.canonical_id
                    """)
                except Exception:
                    c.execute("""
                    SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
                           cq.correct_option_key, cq.legal_reference,
                           im.local_path as image_local_path
                    FROM canonical_questions cq
                    LEFT JOIN images im ON cq.primary_image_id = im.id
                    ORDER BY cq.canonical_id
                    """)
                for r in c.fetchall():
                    r_keys = r.keys() if hasattr(r, "keys") else ()
                    cid = r["canonical_id"]
                    cat_id = r["category_id"] if r["category_id"] is not None else 0
                    new_questions[cid] = {
                        "canonical_id": cid,
                        "category_id": r["category_id"],
                        "category_name": r["category_name"] or "",
                        "has_image": bool(r["has_image"]),
                        "correct_option_key": r["correct_option_key"],
                        "legal_reference": r["legal_reference"],
                        "legal_verification_status": r["legal_verification_status"] if "legal_verification_status" in r_keys else None,
                        "legal_chapter": r["legal_chapter"] if "legal_chapter" in r_keys else None,
                        "legal_clause": r["legal_clause"] if "legal_clause" in r_keys else None,
                        "legal_doc_title": r["legal_doc_title"] if "legal_doc_title" in r_keys else None,
                        "image_local_path": r["image_local_path"] if r["has_image"] else None,
                        "translations": {},
                        "answers": []
                    }
                    new_by_category.setdefault(cat_id, []).append(cid)
                    new_all_ids.append(cid)

                c.execute("SELECT canonical_id, language, question_text, explanation FROM canonical_translations")
                for r in c.fetchall():
                    cid = r["canonical_id"]
                    if cid in new_questions:
                        new_questions[cid]["translations"][r["language"]] = {
                            "question_text": r["question_text"],
                            "explanation": r["explanation"]
                        }

                c.execute("SELECT canonical_id, option_key, text_uz_latn, text_uz_cyrl, text_ru, sort_order FROM canonical_answers ORDER BY sort_order")
                for r in c.fetchall():
                    cid = r["canonical_id"]
                    if cid in new_questions:
                        new_questions[cid]["answers"].append({
                            "option_key": r["option_key"],
                            "text_uz_latn": r["text_uz_latn"],
                            "text_uz_cyrl": r["text_uz_cyrl"],
                            "text_ru": r["text_ru"],
                            "sort_order": r["sort_order"]
                        })

                c.execute("""
                SELECT COALESCE(cq.category_id, 0) as category_id, cq.category_name, COUNT(*) as question_count
                FROM canonical_questions cq
                GROUP BY cq.category_id, cq.category_name
                ORDER BY COALESCE(cq.category_id, 0)
                """)
                new_categories = [dict(r) for r in c.fetchall()]

                self._cache_questions = new_questions
                self._cache_categories = new_categories
                self._by_category = new_by_category
                self._all_canonical_ids = new_all_ids
                self._cache_source = "sql"
                self._cache_revision = db_rev if db_rev is not None else 0
                self._last_revision_check_at = time.monotonic()
            except Exception as e:
                if bundle is not None:
                    logger.warning("CATALOG_BUNDLE_DEGRADED_SQL_UNAVAILABLE: %s", e)
                    self._populate_from_bundle(bundle, source_label="bundle_degraded_sql_unavailable")
                else:
                    logger.debug("Catalog preload fallback (%s); direct queries will be used.", e)
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def ensure_fresh_cache(self, force: bool = False) -> bool:
        """
        Periodically (every 300s TTL or when forced) checks lightweight system_settings['catalog_version'].
        Reloads in-memory caches transparently if DB catalog revision has advanced.
        """
        now = time.monotonic()
        if not force and (now - self._last_revision_check_at) < self.REVISION_CHECK_TTL_SECONDS:
            return False
        try:
            with self._get_connection() as conn:
                db_rev = get_db_catalog_revision(conn)
        except Exception:
            return False

        self._last_revision_check_at = now
        if db_rev is not None and self._cache_revision is not None and db_rev != self._cache_revision:
            logger.info("Catalog drift detected (cached=%s, db=%s); reloading cache.", self._cache_revision, db_rev)
            self.invalidate_cache(reload=True)
            return True
        return False

    def invalidate_cache(self, reload: bool = True):
        """Reloads catalog atomically using copy-on-write replacement to prevent empty-cache reads."""
        if reload:
            self._preload_cache()
        else:
            with self._cache_lock:
                self._cache_questions = {}
                self._cache_categories = []
                self._by_category = {}
                self._all_canonical_ids = []
                self._cache_revision = None
                self._last_revision_check_at = 0.0

    # 1. Language Support
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        return SUPPORTED_LANGUAGES

    # 2. Categories
    def get_categories(self, language: str = "uz_latn") -> List[Dict[str, Any]]:
        self.ensure_fresh_cache()
        if self._cache_categories:
            return [
                {
                    "category_id": r["category_id"],
                    "name": localize_category(r["category_name"], language),
                    "question_count": r["question_count"]
                }
                for r in self._cache_categories
            ]

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT COALESCE(cq.category_id, 0) as category_id, cq.category_name, COUNT(*) as question_count
            FROM canonical_questions cq
            GROUP BY cq.category_id, cq.category_name
            ORDER BY COALESCE(cq.category_id, 0)
            """)
            categories = []
            for row in c.fetchall():
                categories.append({
                    "category_id": row["category_id"],
                    "name": localize_category(row["category_name"], language),
                    "question_count": row["question_count"]
                })
            return categories

    # Helper to construct a QuestionItem in a specified language
    def get_question(self, canonical_id: str, language: str = "uz_latn", include_answer_key: bool = True) -> Optional[QuestionItem]:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{language}'. Choose from {list(SUPPORTED_LANGUAGES.keys())}")

        # Serve from memory cache if available
        if self._cache_questions and canonical_id in self._cache_questions:
            q = self._cache_questions[canonical_id]
            tr = q["translations"].get(language, {})
            lang_col = f"text_{language}"
            options = [
                AnswerOption(
                    option_key=a["option_key"],
                    text=a.get(lang_col, ""),
                    sort_order=a["sort_order"]
                )
                for a in q["answers"]
            ]

            return QuestionItem(
                canonical_id=q["canonical_id"],
                category_id=q["category_id"],
                category_name=localize_category(q["category_name"], language),
                language=language,
                question_text=tr.get("question_text", ""),
                options=options,
                has_image=q["has_image"],
                image_path=q["image_local_path"],
                explanation=tr.get("explanation"),
                legal_reference=localize_legal_reference(q["legal_reference"], language),
                correct_option_key=q["correct_option_key"] if include_answer_key else None,
                legal_verification_status=q.get("legal_verification_status"),
                legal_chapter=q.get("legal_chapter"),
                legal_clause=q.get("legal_clause"),
                legal_doc_title=q.get("legal_doc_title"),
            )

        with self._get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute("""
                SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
                       cq.correct_option_key, cq.legal_reference,
                       cq.legal_verification_status, cq.legal_chapter, cq.legal_clause, cq.legal_doc_title,
                       ct.question_text, ct.explanation,
                       im.local_path as image_local_path
                FROM canonical_questions cq
                JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                LEFT JOIN images im ON cq.primary_image_id = im.id
                WHERE cq.canonical_id = ?
                """, (language, canonical_id))
            except Exception:
                c.execute("""
                SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
                       cq.correct_option_key, cq.legal_reference,
                       ct.question_text, ct.explanation,
                       im.local_path as image_local_path
                FROM canonical_questions cq
                JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                LEFT JOIN images im ON cq.primary_image_id = im.id
                WHERE cq.canonical_id = ?
                """, (language, canonical_id))
            q_row = c.fetchone()
            if not q_row:
                return None

            row_keys = q_row.keys() if hasattr(q_row, "keys") else ()
            # Get answer options in this language
            lang_col = f"text_{language}"
            c.execute(f"""
            SELECT option_key, {lang_col} as ans_text, sort_order
            FROM canonical_answers
            WHERE canonical_id = ?
            ORDER BY sort_order
            """, (canonical_id,))
            
            options = [
                AnswerOption(
                    option_key=a["option_key"],
                    text=a["ans_text"],
                    sort_order=a["sort_order"]
                ) for a in c.fetchall()
            ]

            return QuestionItem(
                canonical_id=q_row["canonical_id"],
                category_id=q_row["category_id"],
                category_name=localize_category(q_row["category_name"], language),
                language=language,
                question_text=q_row["question_text"],
                options=options,
                has_image=bool(q_row["has_image"]),
                image_path=q_row["image_local_path"] if q_row["has_image"] else None,
                explanation=q_row["explanation"],
                legal_reference=localize_legal_reference(q_row["legal_reference"], language),
                correct_option_key=q_row["correct_option_key"] if include_answer_key else None,
                legal_verification_status=q_row["legal_verification_status"] if "legal_verification_status" in row_keys else None,
                legal_chapter=q_row["legal_chapter"] if "legal_chapter" in row_keys else None,
                legal_clause=q_row["legal_clause"] if "legal_clause" in row_keys else None,
                legal_doc_title=q_row["legal_doc_title"] if "legal_doc_title" in row_keys else None,
            )

    # 3. Practice by Category (unseen-first prioritization + offset pagination for >30 categories)
    def get_questions_by_category(
        self,
        category_id: int,
        language: str = "uz_latn",
        limit: Optional[int] = None,
        solved_ids: Optional[set] = None,
        offset: int = 0,
    ) -> List[QuestionItem]:
        if self._by_category:
            qids = list(self._by_category.get(category_id, []))
        else:
            with self._get_connection() as conn:
                c = conn.cursor()
                if category_id == 0:
                    c.execute("SELECT canonical_id FROM canonical_questions WHERE category_id = 0 OR category_id IS NULL")
                else:
                    c.execute("SELECT canonical_id FROM canonical_questions WHERE category_id = ?", (category_id,))
                qids = [row["canonical_id"] for row in c.fetchall()]

        if solved_ids:
            qids = [qid for qid in qids if qid not in solved_ids] + [qid for qid in qids if qid in solved_ids]
        if offset and offset > 0:
            qids = qids[offset:]
        if limit and limit > 0:
            qids = qids[:limit]
        return [q for q in (self.get_question(qid, language=language) for qid in qids if qid) if q]

    # 4. Random Mixed Practice
    def get_random_practice(self, count: int = 10, language: str = "uz_latn") -> List[QuestionItem]:
        if self._all_canonical_ids:
            sample_count = min(count, len(self._all_canonical_ids))
            qids = random.sample(self._all_canonical_ids, sample_count)
            return [self.get_question(qid, language=language) for qid in qids]

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT canonical_id FROM canonical_questions ORDER BY RANDOM() LIMIT ?", (count,))
            qids = [row["canonical_id"] for row in c.fetchall()]

        return [self.get_question(qid, language=language) for qid in qids]

    # 5. 20-Question Exam Simulation
    def create_exam_session(self, language: str = "uz_latn", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cfg = dict(DEFAULT_EXAM_CONFIG)
        if config:
            cfg.update(config)

        total_q = cfg["total_questions"]
        if self._all_canonical_ids:
            sample_count = min(total_q, len(self._all_canonical_ids))
            qids = random.sample(self._all_canonical_ids, sample_count)
        else:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT canonical_id FROM canonical_questions ORDER BY RANDOM() LIMIT ?", (total_q,))
                qids = [row["canonical_id"] for row in c.fetchall()]

        questions = [self.get_question(qid, language=language) for qid in qids]
        session_id = f"EXAM-{int(time.time())}-{random.randint(1000, 9999)}"

        return {
            "session_id": session_id,
            "language": language,
            "created_at": time.time(),
            "time_limit_seconds": cfg["time_limit_seconds"],
            "passing_score": cfg["passing_score"],
            "total_questions": len(questions),
            "questions": questions
        }

    # 6. Immediate Feedback on Submitted Answer
    def check_answer(self, canonical_id: str, submitted_key: str, language: str = "uz_latn") -> QuestionFeedback:
        submitted_key = submitted_key.strip().upper()

        if self._cache_questions and canonical_id in self._cache_questions:
            q = self._cache_questions[canonical_id]
            tr = q["translations"].get(language, {})
            correct_key = q["correct_option_key"]
            is_correct = (submitted_key == correct_key)
            return QuestionFeedback(
                canonical_id=canonical_id,
                submitted_key=submitted_key,
                correct_key=correct_key,
                is_correct=is_correct,
                explanation=tr.get("explanation"),
                legal_reference=localize_legal_reference(q["legal_reference"], language),
                legal_verification_status=q.get("legal_verification_status"),
                legal_chapter=q.get("legal_chapter"),
                legal_clause=q.get("legal_clause"),
                legal_doc_title=q.get("legal_doc_title"),
            )

        with self._get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute("""
                SELECT cq.correct_option_key, cq.legal_reference,
                       cq.legal_verification_status, cq.legal_chapter, cq.legal_clause, cq.legal_doc_title,
                       ct.explanation
                FROM canonical_questions cq
                LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                WHERE cq.canonical_id = ?
                """, (language, canonical_id))
            except Exception:
                c.execute("""
                SELECT cq.correct_option_key, cq.legal_reference, ct.explanation
                FROM canonical_questions cq
                LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                WHERE cq.canonical_id = ?
                """, (language, canonical_id))
            row = c.fetchone()
            if not row:
                raise ValueError(f"Question {canonical_id} not found")

            row_keys = row.keys() if hasattr(row, "keys") else ()
            correct_key = row["correct_option_key"]
            is_correct = (submitted_key == correct_key)

            return QuestionFeedback(
                canonical_id=canonical_id,
                submitted_key=submitted_key,
                correct_key=correct_key,
                is_correct=is_correct,
                explanation=row["explanation"],
                legal_reference=localize_legal_reference(row["legal_reference"], language),
                legal_verification_status=row["legal_verification_status"] if "legal_verification_status" in row_keys else None,
                legal_chapter=row["legal_chapter"] if "legal_chapter" in row_keys else None,
                legal_clause=row["legal_clause"] if "legal_clause" in row_keys else None,
                legal_doc_title=row["legal_doc_title"] if "legal_doc_title" in row_keys else None,
            )

    # 7. Complete Test Evaluation & Error Analysis
    def evaluate_test_session(self, session_id: str, answers_map: Dict[str, str],
                              language: str = "uz_latn", time_elapsed_seconds: float = 0.0,
                              passing_score: int = 18) -> ExamSessionResult:
        """
        answers_map: { 'CANON-YHQ-0001': 'A', 'CANON-YHQ-0002': 'B', ... }
        """
        correct_count = 0
        incorrect_count = 0
        incorrect_qids = []
        category_breakdown: Dict[str, Dict[str, int]] = {}

        for qid, submitted_key in answers_map.items():
            feedback = self.check_answer(qid, submitted_key, language=language)
            q_item = self.get_question(qid, language=language)
            cat_name = q_item.category_name if q_item else "Boshqa"

            if cat_name not in category_breakdown:
                category_breakdown[cat_name] = {"correct": 0, "incorrect": 0, "total": 0}

            category_breakdown[cat_name]["total"] += 1

            if feedback.is_correct:
                correct_count += 1
                category_breakdown[cat_name]["correct"] += 1
            else:
                incorrect_count += 1
                incorrect_qids.append(qid)
                category_breakdown[cat_name]["incorrect"] += 1

        total_q = len(answers_map)
        score_pct = (correct_count / total_q * 100) if total_q > 0 else 0.0
        passed = (correct_count >= passing_score)

        return ExamSessionResult(
            session_id=session_id,
            language=language,
            total_questions=total_q,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            score_percentage=round(score_pct, 1),
            passed=passed,
            time_elapsed_seconds=round(time_elapsed_seconds, 1),
            category_breakdown=category_breakdown,
            incorrect_question_ids=incorrect_qids
        )

    # 8. Retake Incorrect Questions ("Xatolar ustida ishlash")
    def create_mistakes_review_session(self, incorrect_question_ids: List[str], language: str = "uz_latn") -> Dict[str, Any]:
        questions = [self.get_question(qid, language=language) for qid in incorrect_question_ids if qid]
        return {
            "session_id": f"REVIEW-{int(time.time())}",
            "type": "MISTAKES_REVIEW",
            "language": language,
            "total_questions": len(questions),
            "questions": questions
        }

    # 9. Systematic Bilet Tickets (67 Official Billets covering all canonical questions)
    TICKET_SIZE = 20

    def _ordered_all_ids(self) -> List[str]:
        if self._all_canonical_ids:
            return self._all_canonical_ids
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT canonical_id FROM canonical_questions ORDER BY canonical_id")
            return [r["canonical_id"] for r in c.fetchall()]

    def get_total_question_count(self) -> int:
        return len(self._ordered_all_ids())

    def get_ticket_count(self) -> int:
        total = len(self._ordered_all_ids())
        return (total + self.TICKET_SIZE - 1) // self.TICKET_SIZE if total > 0 else 0

    def get_ticket_question_ids(self, ticket_number: int) -> List[str]:
        if ticket_number < 1:
            return []
        all_ids = self._ordered_all_ids()
        start = (ticket_number - 1) * self.TICKET_SIZE
        if start >= len(all_ids):
            return []
        return all_ids[start : start + self.TICKET_SIZE]

    def get_tickets_summary(self, language: str = "uz_latn") -> List[Dict[str, Any]]:
        all_ids = self._ordered_all_ids()
        tickets = []
        total_tickets = (len(all_ids) + self.TICKET_SIZE - 1) // self.TICKET_SIZE
        for idx in range(total_tickets):
            num = idx + 1
            chunk = all_ids[idx * self.TICKET_SIZE : (idx + 1) * self.TICKET_SIZE]
            # Find dominant category for ticket labeling
            cat_counts: Dict[str, int] = {}
            for qid in chunk:
                q_meta = self._cache_questions.get(qid)
                if q_meta:
                    cname = localize_category(q_meta["category_name"], language)
                    cat_counts[cname] = cat_counts.get(cname, 0) + 1
            primary_topic = max(cat_counts.items(), key=lambda kv: kv[1])[0] if cat_counts else ""
            tickets.append({
                "ticket_number": num,
                "question_count": len(chunk),
                "primary_topic": primary_topic,
                "first_canonical_id": chunk[0] if chunk else None,
                "last_canonical_id": chunk[-1] if chunk else None,
            })
        return tickets

    def get_ticket_questions(self, ticket_number: int, language: str = "uz_latn") -> List[QuestionItem]:
        qids = self.get_ticket_question_ids(ticket_number)
        return [q for q in (self.get_question(qid, language=language) for qid in qids) if q]

    # 10. Smart Adaptive & SM-2 Spaced Repetition Selection (Due SRS -> Mistakes -> Weak Categories -> Unseen)
    def get_adaptive_question_ids(
        self,
        count: int = 20,
        unresolved_mistakes: Optional[List[str]] = None,
        weak_category_ids: Optional[List[int]] = None,
        solved_correct_ids: Optional[Set[str]] = None,
        due_srs_ids: Optional[List[str]] = None,
    ) -> List[str]:
        all_ids = self._ordered_all_ids()
        if not all_ids:
            return []

        count = max(1, min(int(count or 20), len(all_ids)))
        selected: List[str] = []
        seen: Set[str] = set()
        solved_set = solved_correct_ids or set()
        valid_set = set(all_ids)

        def add_candidates(pool: List[str], cap: int):
            added = 0
            for qid in pool:
                if len(selected) >= count or added >= cap:
                    break
                if qid in valid_set and qid not in seen:
                    seen.add(qid)
                    selected.append(qid)
                    added += 1

        # Bucket 0: Overdue SM-2 cards first (preserving overdue priority order)
        if due_srs_ids:
            add_candidates(list(due_srs_ids), max(1, int(count * 0.50)))

        # Bucket 1: Unresolved mistakes (up to ~40%)
        mistakes_pool = list(unresolved_mistakes or [])
        random.shuffle(mistakes_pool)
        add_candidates(mistakes_pool, max(1, int(count * 0.40)))

        # Bucket 2: Unsolved or missed questions from weak categories (up to ~45%)
        weak_pool: List[str] = []
        for cid_cat in (weak_category_ids or []):
            cat_qids = list(self._by_category.get(cid_cat, []))
            unsolved_in_cat = [q for q in cat_qids if q not in solved_set]
            random.shuffle(unsolved_in_cat)
            weak_pool.extend(unsolved_in_cat)
        add_candidates(weak_pool, max(2, int(count * 0.45)))

        # Bucket 3: Unseen questions across entire bank
        unseen_pool = [q for q in all_ids if q not in solved_set and q not in seen]
        random.shuffle(unseen_pool)
        add_candidates(unseen_pool, count - len(selected))

        # Bucket 4: General remainder if user solved nearly everything
        if len(selected) < count:
            rest = [q for q in all_ids if q not in seen]
            random.shuffle(rest)
            add_candidates(rest, count - len(selected))

        random.shuffle(selected)
        return selected

    def get_srs_session_question_ids(
        self,
        count: int = 20,
        due_srs_ids: Optional[List[str]] = None,
        unresolved_mistakes: Optional[List[str]] = None,
        weak_category_ids: Optional[List[int]] = None,
        solved_correct_ids: Optional[Set[str]] = None,
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Builds a daily "Aqlli Takrorlash" session queue strictly prioritized by:
        1) Overdue SM-2 items (in urgency order), 2) Active mistakes, 3) Weak categories, 4) Fresh bank items.
        """
        all_ids = self._ordered_all_ids()
        if not all_ids:
            return [], {"due_srs": 0, "mistakes": 0, "weak_or_new": 0}

        count = max(1, min(int(count or 20), len(all_ids)))
        valid_set = set(all_ids)
        solved_set = solved_correct_ids or set()
        selected: List[str] = []
        seen: Set[str] = set()
        counts = {"due_srs": 0, "mistakes": 0, "weak_or_new": 0}

        def take_from(pool: List[str], bucket: str) -> None:
            for qid in pool:
                if len(selected) >= count:
                    break
                if qid in valid_set and qid not in seen:
                    seen.add(qid)
                    selected.append(qid)
                    counts[bucket] += 1

        take_from(list(due_srs_ids or []), "due_srs")
        mistakes_pool = list(unresolved_mistakes or [])
        random.shuffle(mistakes_pool)
        take_from(mistakes_pool, "mistakes")

        weak_pool: List[str] = []
        for cid_cat in (weak_category_ids or []):
            cat_qids = [q for q in self._by_category.get(cid_cat, []) if q not in solved_set and q not in seen]
            random.shuffle(cat_qids)
            weak_pool.extend(cat_qids)
        take_from(weak_pool, "weak_or_new")

        if len(selected) < count:
            unseen = [q for q in all_ids if q not in solved_set and q not in seen]
            random.shuffle(unseen)
            take_from(unseen, "weak_or_new")

        if len(selected) < count:
            rest = [q for q in all_ids if q not in seen]
            random.shuffle(rest)
            take_from(rest, "weak_or_new")

        return selected, counts


def run_interactive_demo():
    print("=" * 60)
    print("   AVTOTEST UZBEKISTAN - 3-LANGUAGE UNIFIED PRODUCT DEMO")
    print("=" * 60)

    # Use staging if available or master
    db_file = "staging_master_database.sqlite" if os.path.exists("staging_master_database.sqlite") else "master_database.sqlite"
    engine = AvtotestProductEngine(db_file)

    print("\n1. Tilni tanlang / Выберите язык:")
    print("   [1] uz_latn: O'zbekcha (Lotin)")
    print("   [2] uz_cyrl: Ўзбекча (Кирилл)")
    print("   [3] ru:      Русский")
    
    lang = "uz_latn"
    print(f"Tanlangan til: {SUPPORTED_LANGUAGES[lang]}")

    print("\n2. Kategoriyalar ro'yxati:")
    cats = engine.get_categories(language=lang)
    for c in cats[:5]:
        print(f"   - {c['name']} (Savollar soni: {c['question_count']})")

    print("\n3. 20 savolli rasmiy davlat imtihoni simulyatsiyasi boshlandi...")
    exam = engine.create_exam_session(language=lang)
    print(f"   Sessiya ID: {exam['session_id']}")
    print(f"   Jami savollar: {exam['total_questions']} ta, Vaqt: {exam['time_limit_seconds'] // 60} daqiqa")

    # Sample testing first 3 questions
    sample_answers = {}
    print("\n--- Namunaviy savollar ---")
    for i, q in enumerate(exam["questions"][:3], 1):
        print(f"\n{i}-savol [{q.canonical_id}]: {q.question_text}")
        if q.has_image:
            print(f"   [Rasm mavjud]: {q.image_path}")
        for opt in q.options:
            print(f"   [{opt.option_key}] {opt.text}")

        # Choose first option as sample answer
        chosen = q.options[0].option_key
        sample_answers[q.canonical_id] = chosen
        fb = engine.check_answer(q.canonical_id, chosen, language=lang)
        status_str = "TO'G'RI" if fb.is_correct else "NOTO'G'RI"
        print(f"   Natija: {status_str} (To'g'ri javob: [{fb.correct_key}])")
        if fb.explanation:
            print(f"   Izoh: {fb.explanation[:90]}...")

    print("\n4. Test yakunlandi va natija tahlili:")
    res = engine.evaluate_test_session(exam["session_id"], sample_answers, language=lang, time_elapsed_seconds=45.2)
    print(f"   Natija: {res.correct_count}/{res.total_questions} to'g'ri ({res.score_percentage}%)")
    print(f"   Status: {'IMTIHONDAN O‘TDI' if res.passed else 'YIQILDI'}")
    print(f"   Kategoriyalar bo'yicha tahlil: {len(res.category_breakdown)} ta kategoriya qamrab olindi")

    if res.incorrect_question_ids:
        print("\n5. Xatolar ustida ishlash sessiyasi:")
        review = engine.create_mistakes_review_session(res.incorrect_question_ids, language=lang)
        print(f"   Qayta ishlash uchun ajratilgan xato savollar: {review['total_questions']} ta")

    print("\n" + "=" * 60)
    print("   PRODUCT ENGINE TAYYOR VA INTEGRATSIYAGA TO'LIQ MOS!")
    print("=" * 60)

if __name__ == "__main__":
    run_interactive_demo()
