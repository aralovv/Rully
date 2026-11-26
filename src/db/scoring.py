"""
RULLY Multi-Criteria Driver Accuracy & Exam Readiness Calibration Engine.
Pure scoring functions separated cleanly from database repository concerns.
Calibrated for Uzbekistan State Driving Examination (VMQ 408 / 172).
"""

import math
from typing import Any, Dict, Optional, Union


def compute_driver_accuracy(
    total_answered: int,
    correct_answers: int,
    unique_questions: int = 0,
    unique_correct: int = 0,
    recent_total: int = 0,
    recent_correct: int = 0,
    categories_tested: int = 0,
    unresolved_mistakes: int = 0,
    return_details: bool = False,
    srs_mastered: int = 0,
    srs_due: int = 0,
    srs_tracked: int = 0,
) -> Union[float, Dict[str, Any]]:
    """
    RULLY Multi-Criteria Driver Accuracy Engine (0.0 to 100.0%).
    Evaluates knowledge precision across net above-guessing score, recency,
    distinct question mastery, cross-category breadth, Bayesian confidence, and SM-2 retention.
    """
    if total_answered <= 0 or correct_answers <= 0:
        if return_details:
            return {
                "accuracy": 0.0,
                "raw_accuracy": 0.0,
                "net_knowledge_score": 0.0,
                "recent_accuracy": 0.0,
                "distinct_accuracy": 0.0,
                "confidence_factor": 0.0,
                "bayesian_accuracy": 0.0,
                "srs_retention_rate": 100.0,
            }
        return 0.0

    raw_acc = min(100.0, max(0.0, (correct_answers / total_answered) * 100.0))
    bayesian_acc = ((correct_answers + 1.0) / (total_answered + 4.0)) * 100.0

    # 1. Net Knowledge Accuracy above 25% random-guessing baseline (40% weight)
    net_acc = 0.0 if raw_acc <= 25.0 else min(100.0, max(0.0, ((raw_acc - 25.0) / 70.0) * 100.0))

    # 2. Recent Accuracy (30% weight)
    recent_acc = min(100.0, max(0.0, (recent_correct / recent_total) * 100.0)) if recent_total > 0 else raw_acc

    # 3. Distinct Questions Accuracy (20% weight)
    distinct_acc = (
        min(100.0, max(0.0, (unique_correct / unique_questions) * 100.0))
        if (unique_questions > 0 and unique_correct > 0)
        else raw_acc
    )

    # 4. Cross-Category Balance (10% weight)
    cat_count = categories_tested or 0
    cat_factor = min(100.0, (cat_count / 12.0) * 100.0) if cat_count > 0 else distinct_acc

    composite = 0.40 * net_acc + 0.30 * recent_acc + 0.20 * distinct_acc + 0.10 * cat_factor

    # 5. Smooth Bayesian Sample-Size Confidence Curve
    if total_answered < 35:
        confidence = min(1.0, 0.38 + 0.62 * math.sqrt(total_answered / 35.0))
    else:
        confidence = 1.0

    final_acc = composite * confidence

    # Phase 5 SM-2 Retention Adjustment (strictly bounded [-3.0, +2.5], neutral when srs_tracked == 0)
    srs_retention = 100.0
    if srs_tracked > 0:
        bounded_due = min(srs_tracked, max(0, srs_due))
        srs_retention = round(((srs_tracked - bounded_due) / srs_tracked) * 100.0, 1)
        if srs_tracked >= 10:
            mastery_ratio = min(1.0, max(0.0, srs_mastered / srs_tracked))
            due_ratio = bounded_due / srs_tracked
            if mastery_ratio >= 0.4 and bounded_due <= 3:
                final_acc += min(2.5, mastery_ratio * 2.5)
            elif due_ratio > 0.45 and bounded_due >= 15:
                final_acc -= min(3.0, (due_ratio - 0.45) * 6.0)

    if raw_acc <= 25.0:
        final_acc = min(final_acc, 8.0)
    if unresolved_mistakes >= 15:
        final_acc = min(final_acc, 65.0)
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
            "confidence_factor": round(confidence, 2),
            "bayesian_accuracy": round(bayesian_acc, 1),
            "srs_retention_rate": srs_retention,
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
    categories_tested: Optional[int] = None,
    resolved_mistakes: int = 0,
    current_streak: int = 0,
    avg_exam_time_seconds: float = 0.0,
    recent_pass_rate: Optional[float] = None,
    return_details: bool = False,
    srs_mastered: int = 0,
    srs_due: int = 0,
    srs_tracked: int = 0,
) -> Union[float, Dict[str, Any]]:
    """
    RULLY Intelligent 5-Pillar Exam Readiness Engine (0.0 to 100.0%).
    Uses smooth continuous curves without sudden punitive mid-journey cliffs
    while enforcing anti-guessing and state-exam pass gates.
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
                "pace_and_streak": 0.0,
            },
        }
        return details if return_details else 0.0

    # Pillar 1: Exam Passing Mastery & Consistency (30%)
    if passed_exams == 0:
        p_exam = 0.0
    else:
        rec_pass = recent_pass_rate if recent_pass_rate is not None else pass_rate
        consistency = min(1.0, passed_exams / 4.0)
        p_exam = min(100.0, (0.40 * pass_rate + 0.60 * rec_pass) * (0.35 + 0.65 * consistency))

    # Pillar 2: Knowledge Accuracy above 35% baseline (25%)
    if total_answered < 10 or accuracy <= 35.0:
        p_acc = 0.0
    else:
        p_acc = min(100.0, max(0.0, ((accuracy - 35.0) / 57.0) * 100.0))

    # Pillar 3: Curriculum / Syllabus Coverage (25%)
    if categories_tested is None or categories_tested <= 0:
        categories_tested = min(43, max(1, int(unique_questions / 8)))
    q_score = min(100.0, (unique_questions / 160.0) * 100.0)
    cat_score = min(100.0, (categories_tested / 20.0) * 100.0)
    p_cov = 0.60 * q_score + 0.40 * cat_score

    # Pillar 4: Mistake Bank Hygiene (10%)
    if total_answered < 5:
        p_mistakes = 50.0
    elif unresolved_mistakes == 0:
        p_mistakes = 100.0
    else:
        penalty = unresolved_mistakes * 5.0
        total_m = resolved_mistakes + unresolved_mistakes
        res_bonus = (resolved_mistakes / total_m * 20.0) if total_m > 0 else 0.0
        p_mistakes = max(0.0, min(100.0, 100.0 - penalty + res_bonus))

    # Pillar 5: Exam Pace & Practice Regularity (10%)
    if current_streak > 0:
        s_score = min(100.0, max(30.0, current_streak * 25.0))
    else:
        s_score = 100.0 if passed_exams >= 4 else (0.0 if total_exams > 0 and passed_exams == 0 else 50.0)

    if avg_exam_time_seconds <= 0:
        t_score = 100.0 if passed_exams >= 4 else (0.0 if total_exams > 0 and passed_exams == 0 else 50.0)
    elif 200 <= avg_exam_time_seconds <= 1100:
        t_score = 100.0
    elif avg_exam_time_seconds < 200:
        t_score = 30.0
    else:
        t_score = max(30.0, 100.0 - ((avg_exam_time_seconds - 1100) / 400.0) * 50.0)
    p_pace = 0.50 * s_score + 0.50 * t_score

    raw_score = 0.30 * p_exam + 0.25 * p_acc + 0.25 * p_cov + 0.10 * p_mistakes + 0.10 * p_pace

    # Continuous square-root sample confidence scaling up to 100 questions (avoids arbitrary cliffs)
    if total_answered < 100:
        conf_multiplier = min(1.0, max(0.22, math.sqrt(total_answered / 100.0)))
        raw_score = raw_score * conf_multiplier

    # Smooth pass-count ceiling: allows up to 20% from practice alone before passing state exam,
    # scaling smoothly (0 -> 20%, 1 -> 52%, 2 -> 74%, 3+ -> 100%)
    if passed_exams == 0:
        final_score = min(raw_score, 20.0)
    elif passed_exams == 1:
        final_score = min(raw_score, 52.0)
    elif passed_exams == 2:
        final_score = min(raw_score, 74.0)
    else:
        final_score = raw_score

    if accuracy <= 30.0:
        final_score = min(final_score, 8.0)

    if unresolved_mistakes >= 40:
        final_score = min(final_score, 20.0)
    elif unresolved_mistakes >= 25:
        final_score = min(final_score, 35.0)
    elif unresolved_mistakes >= 15:
        final_score = min(final_score, 55.0)

    srs_retention_pct = 100.0
    if srs_tracked > 0:
        bounded_due = min(srs_tracked, max(0, srs_due))
        srs_retention_pct = round(((srs_tracked - bounded_due) / srs_tracked) * 100.0, 1)
        if srs_tracked >= 10 and passed_exams >= 1:
            mastery_ratio = min(1.0, max(0.0, srs_mastered / srs_tracked))
            due_ratio = bounded_due / srs_tracked
            if mastery_ratio >= 0.5 and bounded_due <= 3:
                final_score += min(2.0, mastery_ratio * 2.0)
            elif due_ratio > 0.5 and bounded_due >= 15:
                final_score -= min(3.0, (due_ratio - 0.5) * 6.0)

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
        "srs_retention_pct": srs_retention_pct,
        "pillars": {
            "exam_mastery": round(p_exam, 1),
            "accuracy": round(p_acc, 1),
            "coverage": round(p_cov, 1),
            "mistake_hygiene": round(p_mistakes, 1),
            "pace_and_streak": round(p_pace, 1),
        },
    }
    return details if return_details else final_score
