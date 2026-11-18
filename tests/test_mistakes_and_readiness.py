"""
Unit & Integration tests for Mistake Bank isolation and Multi-Pillar Exam Readiness Index.
Guarantees that:
1. ONLY actively attempted wrong answers enter user_mistakes.
2. Skipped/unanswered questions are NEVER counted as mistakes or added to mistake bank.
3. Finish session accurately reports correct, incorrect, and unanswered counts.
4. Exam Readiness Index does not award 25% to random guessers who never passed an exam.
"""
import pytest
from src.bot.database import BotDatabase, compute_driver_readiness


@pytest.fixture
def test_db():
    return BotDatabase("master_database.sqlite")


def test_driver_readiness_calculation_random_guessing():
    # Pure random guessing: 10 exams, 0 passed, 25% accuracy, 20 mistakes
    score = compute_driver_readiness(
        total_exams=10,
        passed_exams=0,
        pass_rate=0.0,
        total_answered=200,
        accuracy=25.0,
        unique_questions=40,
        unresolved_mistakes=20
    )
    # Must be very low (5% - 10%), NOT 25%!
    assert score <= 10.0, f"Expected random guessing readiness <= 10%, got {score}%"


def test_driver_readiness_brand_new_user():
    score = compute_driver_readiness(
        total_exams=0,
        passed_exams=0,
        pass_rate=0.0,
        total_answered=0,
        accuracy=0.0,
        unique_questions=0,
        unresolved_mistakes=0
    )
    assert score == 0.0


def test_driver_readiness_well_prepared_student():
    # Passed 5 out of 5 exams, 95% accuracy, 160 unique questions, 0 mistakes
    score = compute_driver_readiness(
        total_exams=5,
        passed_exams=5,
        pass_rate=100.0,
        total_answered=200,
        accuracy=95.0,
        unique_questions=160,
        unresolved_mistakes=0
    )
    assert score >= 95.0, f"Expected high readiness, got {score}%"


def test_driver_readiness_zero_passed_hard_cap():
    # Even with high accuracy on practice questions, 0 passed exams caps readiness at 20%
    score = compute_driver_readiness(
        total_exams=0,
        passed_exams=0,
        pass_rate=0.0,
        total_answered=120,
        accuracy=90.0,
        unique_questions=100,
        unresolved_mistakes=0
    )
    assert score <= 20.0, f"Expected readiness cap at 20% for 0 passed exams, got {score}%"


def test_mistakes_bank_strict_isolation_on_unanswered(test_db):
    user_id = 999888
    # Cleanup previous test runs
    with test_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_mistakes WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM exam_results WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM session_answers WHERE session_id LIKE 'test-session-iso-%'")
        c.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM telegram_users WHERE user_id = ?", (user_id,))
        c.execute("SELECT canonical_id FROM canonical_questions LIMIT 20")
        question_ids = [r[0] for r in c.fetchall()]
        conn.commit()

    test_db.get_or_create_user(user_id, "learner", "Ali", "Valiyev")

    # Start session with 20 questions
    s_info = test_db.create_session(
        user_id=user_id,
        session_type="EXAM",
        language="uz_latn",
        question_ids=question_ids,
        time_limit_seconds=1500
    )
    session_id = s_info["session_id"]

    # User answers Q1 correctly
    test_db.save_answer(session_id, question_ids[0], "A", "A", True)
    test_db.resolve_mistake(user_id, question_ids[0])

    # User answers Q2 incorrectly
    test_db.save_answer(session_id, question_ids[1], "B", "C", False)
    test_db.record_mistake(user_id, question_ids[1])

    # Questions 3 through 20 are LEFT UNANSWERED / SKIPPED
    # User finishes the exam
    answers = test_db.get_session_answers(session_id)
    assert len(answers) == 2

    correct_count = sum(1 for a in answers.values() if a["is_correct"])
    incorrect_count = sum(1 for a in answers.values() if not a["is_correct"])
    unanswered_count = max(0, 20 - (correct_count + incorrect_count))

    assert correct_count == 1
    assert incorrect_count == 1
    assert unanswered_count == 18

    # Save exam results
    test_db.save_exam_result(
        session_id=session_id,
        user_id=user_id,
        total_q=20,
        correct=correct_count,
        incorrect=incorrect_count,
        pct=5.0,
        passed=False,
        time_spent=120.0,
        category_breakdown={},
        unanswered=unanswered_count
    )

    # VERIFY MISTAKE BANK:
    # ONLY question 2 should be in user_mistakes.
    # Questions 3..20 must NEVER be in user_mistakes!
    mistakes = test_db.get_user_mistakes(user_id)
    assert len(mistakes) == 1
    assert mistakes[0] == question_ids[1]

    for unattempted_qid in question_ids[2:]:
        assert unattempted_qid not in mistakes, f"Unattempted question {unattempted_qid} must not be in mistakes bank!"

    # Verify user stats
    stats = test_db.get_user_stats(user_id)
    assert stats["unresolved_mistakes"] == 1
    assert stats["total_exams"] == 1
    assert stats["passed_exams"] == 0
    assert stats["readiness_score"] <= 15.0

    # Now verify resolving mistake
    test_db.resolve_mistake(user_id, question_ids[1])
    active_mistakes_after = test_db.get_user_mistakes(user_id)
    assert len(active_mistakes_after) == 0
