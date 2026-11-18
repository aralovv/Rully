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
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from src.bot.category_localization import localize_category, localize_legal_reference
from src.db_adapter import get_db_connection, is_turso_enabled

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

@dataclass
class QuestionFeedback:
    canonical_id: str
    submitted_key: str
    correct_key: str
    is_correct: bool
    explanation: Optional[str]
    legal_reference: Optional[str]

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
    def __init__(self, db_path: str = "master_database.sqlite"):
        self.db_path = db_path
        if not is_turso_enabled() and not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def _get_connection(self):
        return get_db_connection(self.db_path)

    # 1. Language Support
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        return SUPPORTED_LANGUAGES

    # 2. Categories
    def get_categories(self, language: str = "uz_latn") -> List[Dict[str, Any]]:
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
    def get_question(self, canonical_id: str, language: str = "uz_latn", include_answer_key: bool = False) -> Optional[QuestionItem]:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language '{language}'. Choose from {list(SUPPORTED_LANGUAGES.keys())}")

        with self._get_connection() as conn:
            c = conn.cursor()
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
                correct_option_key=q_row["correct_option_key"] if include_answer_key else None
            )

    # 3. Practice by Category
    def get_questions_by_category(self, category_id: int, language: str = "uz_latn", limit: Optional[int] = None) -> List[QuestionItem]:
        with self._get_connection() as conn:
            c = conn.cursor()
            if category_id == 0:
                query = "SELECT canonical_id FROM canonical_questions WHERE category_id = 0 OR category_id IS NULL"
                params = []
            else:
                query = "SELECT canonical_id FROM canonical_questions WHERE category_id = ?"
                params = [category_id]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            c.execute(query, params)
            qids = [row["canonical_id"] for row in c.fetchall()]

        return [self.get_question(qid, language=language) for qid in qids]

    # 4. Random Mixed Practice
    def get_random_practice(self, count: int = 10, language: str = "uz_latn") -> List[QuestionItem]:
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
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT cq.correct_option_key, cq.legal_reference, ct.explanation
            FROM canonical_questions cq
            LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
            WHERE cq.canonical_id = ?
            """, (language, canonical_id))
            row = c.fetchone()
            if not row:
                raise ValueError(f"Question {canonical_id} not found")

            correct_key = row["correct_option_key"]
            is_correct = (submitted_key == correct_key)

            return QuestionFeedback(
                canonical_id=canonical_id,
                submitted_key=submitted_key,
                correct_key=correct_key,
                is_correct=is_correct,
                explanation=row["explanation"],
                legal_reference=row["legal_reference"]
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
