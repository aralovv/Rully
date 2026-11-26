"""
RULLY 2.0 SM-2 Spaced Repetition Engine (`Phase 5`).
Implements calibrated SuperMemo SM-2 recall quality derivation, ease-factor bounds,
lapse recovery, mastery classification, and atomic SQLite/Turso upsert builders.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

SM2_MIN_EASE_FACTOR = 1.3
SM2_MAX_EASE_FACTOR = 3.0
SM2_DEFAULT_EASE_FACTOR = 2.5
SM2_MAX_INTERVAL_DAYS = 180

RATING_TO_QUALITY: Dict[str, int] = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
}


def clamp_sm2_quality(quality: int) -> int:
    """Clamps recall quality to standard SM-2 range [0, 5]."""
    return max(0, min(5, int(quality)))


def derive_sm2_quality(
    is_correct: bool,
    session_type: str = "CATEGORY",
    response_time_ms: Optional[int] = None,
    previous_lapses: int = 0,
    explicit_quality: Optional[int] = None,
) -> int:
    """
    Determines SM-2 recall quality (0..5) from an explicit rating or behavioral quiz signals:
    - Explicit rating (0..5) is respected directly when provided.
    - Wrong answers map to quality 1 (fast misclick or repeated lapse) or 2 (familiar error).
    - Correct answers map to quality 3 (slow/mistake-drill recovery), 4 (standard), or 5 (fluent recall).
    """
    if explicit_quality is not None:
        return clamp_sm2_quality(explicit_quality)

    rt = int(response_time_ms) if response_time_ms is not None and response_time_ms >= 0 else None
    stype = (session_type or "CATEGORY").upper()

    if not is_correct:
        if previous_lapses >= 2 or (rt is not None and rt < 2500):
            return 1
        return 2

    if stype == "MISTAKES" or (rt is not None and rt > 20000):
        return 3

    if rt is not None and 1500 <= rt <= 7000 and stype in ("SRS", "ADAPTIVE", "EXAM", "BILET"):
        return 5

    return 4


def classify_srs_mastery(
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    lapses: int = 0,
) -> str:
    """Classifies card retention state cleanly into LEARNING, REVIEWING, or MASTERED."""
    if repetitions <= 0 or (repetitions == 1 and lapses > 1):
        return "LEARNING"
    if repetitions >= 3 and interval_days >= 21 and ease_factor >= 2.0:
        return "MASTERED"
    return "REVIEWING"


def compute_next_sm2_state(
    prev_state: Optional[Dict[str, Any]],
    quality: int,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Computes the next SM-2 scheduling transition from previous card state and recall quality (0..5).
    Failed recalls (quality < 3) reset repetitions to 0, increment lapses, and set next_review_at
    immediately (0-day interval) so missed items enter the daily "Aqlli Takrorlash" queue at once.
    """
    now_dt = now or datetime.utcnow()
    q = clamp_sm2_quality(quality)

    prev = prev_state or {}
    prev_ef = float(prev.get("ease_factor") if prev.get("ease_factor") is not None else SM2_DEFAULT_EASE_FACTOR)
    prev_interval = int(prev.get("interval_days") or 0)
    prev_reps = int(prev.get("repetitions") or 0)
    prev_lapses = int(prev.get("lapses") or 0)

    # Classic SM-2 ease-factor update with educational floor & ceiling
    delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    new_ef = max(SM2_MIN_EASE_FACTOR, min(SM2_MAX_EASE_FACTOR, round(prev_ef + delta, 4)))

    if q < 3:
        new_reps = 0
        new_lapses = prev_lapses + 1
        new_interval = 0
        next_due_dt = now_dt
    else:
        new_reps = prev_reps + 1
        new_lapses = prev_lapses
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = 6
        else:
            base = max(6, prev_interval)
            new_interval = min(SM2_MAX_INTERVAL_DAYS, max(6, int(round(base * new_ef))))
        next_due_dt = now_dt + timedelta(days=new_interval)

    now_iso = now_dt.isoformat()
    next_iso = next_due_dt.isoformat()
    mastery = classify_srs_mastery(new_reps, new_interval, new_ef, new_lapses)

    return {
        "ease_factor": round(new_ef, 2),
        "interval_days": new_interval,
        "repetitions": new_reps,
        "lapses": new_lapses,
        "last_quality": q,
        "last_reviewed_at": now_iso,
        "next_review_at": next_iso,
        "mastery_level": mastery,
        "is_due": new_interval == 0,
    }


def build_srs_upsert_stmt(
    user_id: int,
    canonical_id: str,
    state: Dict[str, Any],
) -> Tuple[str, List[Any]]:
    """
    Returns an atomic idempotent UPSERT statement for user_question_srs compatible with
    both local SQLite and remote Turso execute_batch().
    """
    sql = """
    INSERT INTO user_question_srs (
        user_id, canonical_id, ease_factor, interval_days,
        repetitions, lapses, last_quality, last_reviewed_at, next_review_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, canonical_id) DO UPDATE SET
        ease_factor = excluded.ease_factor,
        interval_days = excluded.interval_days,
        repetitions = excluded.repetitions,
        lapses = excluded.lapses,
        last_quality = excluded.last_quality,
        last_reviewed_at = excluded.last_reviewed_at,
        next_review_at = excluded.next_review_at
    """
    params = [
        int(user_id),
        str(canonical_id),
        float(state["ease_factor"]),
        int(state["interval_days"]),
        int(state["repetitions"]),
        int(state["lapses"]),
        int(state["last_quality"]),
        str(state["last_reviewed_at"]),
        str(state["next_review_at"]),
    ]
    return (sql.strip(), params)
