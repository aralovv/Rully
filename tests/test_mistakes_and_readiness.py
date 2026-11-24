"""
Unit & Integration tests for Mistake Bank isolation and Multi-Pillar Exam Readiness Index.
Guarantees that:
1. ONLY actively attempted wrong answers enter user_mistakes.
2. Skipped/unanswered questions are NEVER counted as mistakes or added to mistake bank.
3. Finish session accurately reports correct, incorrect, and unanswered counts.
4. Exam Readiness Index does not award 25% to random guessers who never passed an exam.
"""
import pytest
from src.bot.database import BotDatabase, compute_driver_readiness, compute_driver_accuracy


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


def test_driver_accuracy_brand_new_user():
    acc = compute_driver_accuracy(total_answered=0, correct_answers=0)
    assert acc == 0.0


def test_driver_accuracy_random_guesser():
    # 200 questions answered, only 50 correct (25% random guessing), 20 unresolved mistakes
    acc = compute_driver_accuracy(
        total_answered=200,
        correct_answers=50,
        unique_questions=60,
        unique_correct=15,
        recent_total=40,
        recent_correct=10,
        categories_tested=3,
        unresolved_mistakes=20
    )
    assert acc <= 10.0, f"Expected guessing accuracy <= 10.0%, got {acc}%"


def test_driver_accuracy_single_answer_confidence_scaling():
    # Answering 1 question correctly must NOT give 100% accuracy due to Bayesian sample size confidence!
    acc = compute_driver_accuracy(
        total_answered=1,
        correct_answers=1,
        unique_questions=1,
        unique_correct=1
    )
    assert acc <= 45.0, f"Single answer must not give fake 100% accuracy, got {acc}%"
    assert acc > 0.0


def test_driver_accuracy_well_prepared_student():
    # 200 questions, 192 correct, 160 unique, 155 unique correct, recent 40/40, 15 categories
    acc = compute_driver_accuracy(
        total_answered=200,
        correct_answers=192,
        unique_questions=160,
        unique_correct=155,
        recent_total=40,
        recent_correct=40,
        categories_tested=15,
        unresolved_mistakes=0
    )
    assert acc >= 95.0, f"Expected high accuracy >= 95.0%, got {acc}%"


def test_driver_accuracy_improving_student_recency_lift():
    # Overall raw is 65% (130/200), but last 40 questions are 38/40 (95%)
    acc_info = compute_driver_accuracy(
        total_answered=200,
        correct_answers=130,
        unique_questions=140,
        unique_correct=100,
        recent_total=40,
        recent_correct=38,
        categories_tested=12,
        unresolved_mistakes=2,
        return_details=True
    )
    assert acc_info["accuracy"] > 65.0, f"Recency trend must lift accuracy above raw 65%, got {acc_info['accuracy']}%"
    assert acc_info["recent_accuracy"] == 95.0


def test_mistakes_bank_strict_isolation_on_unanswered(test_db):
    user_id = 999888
    # Cleanup previous test runs
    with test_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_mistakes WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM exam_results WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM session_answers WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)", (user_id,))
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

    # Clean up test session answers and sessions
    with test_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM session_answers WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM telegram_users WHERE user_id = ?", (user_id,))
        conn.commit()


def test_process_session_answer_resolves_mistakes_in_exam_and_custom(test_db):
    user_id = 999777
    with test_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT canonical_id FROM canonical_questions LIMIT 2")
        qids = [r["canonical_id"] for r in c.fetchall()]
    assert len(qids) >= 2, "Need at least 2 canonical questions in database for test"

    qid_exam, qid_custom = qids[0], qids[1]
    test_db.get_or_create_user(user_id, "tester_mistake_res", "Test", "User")

    try:
        # 1. Test in EXAM mode
        test_db.record_mistake(user_id, qid_exam)
        assert qid_exam in test_db.get_user_mistakes(user_id)

        session_exam = test_db.create_session(user_id, session_type="EXAM", language="uz_latn", question_ids=[qid_exam])
        res_exam = test_db.process_session_answer(
            session_id=session_exam["session_id"],
            user_id=user_id,
            canonical_id=qid_exam,
            selected_key="A",
            correct_key="A",
            is_correct=True,
            session_type="EXAM"
        )
        assert res_exam["is_new"] is True
        assert qid_exam not in test_db.get_user_mistakes(user_id)

        # 2. Test in CUSTOM mode
        test_db.record_mistake(user_id, qid_custom)
        assert qid_custom in test_db.get_user_mistakes(user_id)

        session_custom = test_db.create_session(user_id, session_type="CUSTOM", language="uz_latn", question_ids=[qid_custom])
        res_custom = test_db.process_session_answer(
            session_id=session_custom["session_id"],
            user_id=user_id,
            canonical_id=qid_custom,
            selected_key="B",
            correct_key="B",
            is_correct=True,
            session_type="CUSTOM"
        )
        assert res_custom["is_new"] is True
        assert qid_custom not in test_db.get_user_mistakes(user_id)

    finally:
        with test_db._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM session_answers WHERE session_id IN (SELECT session_id FROM user_sessions WHERE user_id = ?)", (user_id,))
            c.execute("DELETE FROM user_mistakes WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM telegram_users WHERE user_id = ?", (user_id,))
            conn.commit()


def test_graduated_readiness_mistake_tiers():
    # Student with good track record: 5 exams, 4 passed (80%), 200 questions, 85% accuracy
    # Under old logic, 16 active mistakes would crush score to <= 8.0%.
    # Under new graduated logic:
    # 1. 16 mistakes (>= 15) must be capped at 55.0%, and significantly higher than 8.0%!
    score_16 = compute_driver_readiness(
        total_exams=5,
        passed_exams=4,
        pass_rate=80.0,
        total_answered=200,
        accuracy=85.0,
        unique_questions=150,
        unresolved_mistakes=16
    )
    assert 8.0 < score_16 <= 55.0, f"Expected 16 mistakes capped at 55%, got {score_16}%"

    # 2. 26 mistakes (>= 25) must be capped at 35.0%
    score_26 = compute_driver_readiness(
        total_exams=5,
        passed_exams=4,
        pass_rate=80.0,
        total_answered=200,
        accuracy=85.0,
        unique_questions=150,
        unresolved_mistakes=26
    )
    assert 8.0 < score_26 <= 35.0, f"Expected 26 mistakes capped at 35%, got {score_26}%"

    # 3. 42 mistakes (>= 40) must be capped at 20.0%
    score_42 = compute_driver_readiness(
        total_exams=5,
        passed_exams=4,
        pass_rate=80.0,
        total_answered=200,
        accuracy=85.0,
        unique_questions=150,
        unresolved_mistakes=42
    )
    assert score_42 <= 20.0, f"Expected 42 mistakes capped at 20%, got {score_42}%"

