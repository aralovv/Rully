"""
Theory Exam and Category Practice API endpoints for RULLY Mini App.
"""

import os
import json
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_db
from src.api.routes_auth import invalidate_auth_cache
from src.analytics.tracker import log_user_event
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine, QuestionItem
from src.bot.category_localization import localize_category
from src.db.reference_catalog import get_law_reference, get_road_signs_reference
from src.security.rate_limiter import rate_limiter, BoundedTTLCache, get_client_ip

router = APIRouter(prefix="/api", tags=["Theory & Exam"])
engine = AvtotestProductEngine(os.getenv("DB_PATH", "master_database.sqlite"))

# 1. Categories cache (clears cleanly when engine or admin updates catalog_version)
_categories_cache = BoundedTTLCache[str, Any](maxsize=16, ttl_seconds=300.0)


def invalidate_theory_caches(reload_engine: bool = True):
    """Evicts API category cache and reloads AvtotestProductEngine catalog cache."""
    _categories_cache.clear()
    engine.invalidate_cache(reload=reload_engine)

def serialize_question(q: QuestionItem, is_bookmarked: bool = False, include_correct: bool = False) -> Dict[str, Any]:
    image_url = None
    if q.has_image and q.image_path:
        filename = os.path.basename(q.image_path.replace("\\", "/"))
        cdn_base = os.getenv("IMAGE_CDN_BASE_URL", "").rstrip("/")
        image_url = f"{cdn_base}/{filename}" if cdn_base else f"/images/{filename}"

    correct_answer_text = None
    if include_correct and q.correct_option_key:
        correct_opt = next((opt for opt in q.options if opt.option_key == q.correct_option_key), None)
        if correct_opt:
            correct_answer_text = correct_opt.text

    return {
        "canonical_id": q.canonical_id,
        "category_id": q.category_id,
        "category_name": q.category_name,
        "language": q.language,
        "question_text": q.question_text,
        "options": [
            {
                "option_key": opt.option_key,
                "text": opt.text,
                "sort_order": opt.sort_order
            }
            for opt in q.options
        ],
        "has_image": q.has_image,
        "image_url": image_url,
        "legal_reference": q.legal_reference,
        "legal_verification_status": getattr(q, "legal_verification_status", None),
        "legal_chapter": getattr(q, "legal_chapter", None),
        "legal_clause": getattr(q, "legal_clause", None),
        "legal_doc_title": getattr(q, "legal_doc_title", None),
        "explanation": q.explanation if include_correct else None,
        "correct_option_key": q.correct_option_key if include_correct else None,
        "correct_answer_text": correct_answer_text,
        "is_bookmarked": is_bookmarked
    }

@router.get("/categories")
def list_categories(
    response: Response,
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    selected_lang = lang or user.get("language", "uz_latn")
    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"

    if engine.ensure_fresh_cache():
        _categories_cache.clear()

    cached = _categories_cache.get(selected_lang)
    if cached is not None:
        categories = cached
    else:
        categories = engine.get_categories(selected_lang)
        _categories_cache.set(selected_lang, categories)

    rev = engine._cache_revision if engine._cache_revision is not None else 0
    response.headers["ETag"] = f'"rully-cat-{selected_lang}-r{rev}"'
    response.headers["Cache-Control"] = "private, no-store"

    return {
        "language": selected_lang,
        "catalog_revision": rev,
        "count": len(categories),
        "categories": categories
    }

# 2. Get Single Question
@router.get("/questions/{canonical_id}")
def get_question(
    canonical_id: str,
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    selected_lang = lang or user.get("language", "uz_latn")
    q = engine.get_question(canonical_id, language=selected_lang, include_answer_key=True)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    
    is_bm = db.is_bookmarked(user["user_id"], canonical_id)
    return serialize_question(q, is_bookmarked=is_bm, include_correct=True)

# 3. Start Session (Exam, Category, Random, Mistakes, Custom, Bilet, Adaptive, SRS)
class SessionStartRequest(BaseModel):
    session_type: str = Field(..., pattern="^(EXAM|CATEGORY|RANDOM|MISTAKES|CUSTOM|BILET|ADAPTIVE|SRS)$")
    category_id: Optional[int] = None
    ticket_number: Optional[int] = None
    total_questions: Optional[int] = 20
    offset: Optional[int] = 0
    time_limit_seconds: Optional[int] = 25 * 60
    show_answer: Optional[bool] = True
    show_explanation: Optional[bool] = True
    language: Optional[str] = None

@router.post("/session/start")
def start_session(
    req: SessionStartRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]

    # Rate limiting (P0): max 10 session start requests per minute per user
    allowed, _, retry_after = rate_limiter.is_allowed(f"session_start:{user_id}", max_requests=10, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many session start requests. Please wait {int(retry_after)}s before starting another session."
        )

    lang = req.language or user.get("language", "uz_latn")
    if lang not in ["uz_latn", "uz_cyrl", "ru"]:
        lang = "uz_latn"

    # Batch ALL prerequisite DB reads (subscription/free-tier + mode-specific state + bookmarks) into 1 RT!
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    from src.db_adapter import fetch_batch_dicts
    from src.db.tz_utils import evaluate_subscription_row, compute_free_tier_from_counts
    from src.db.sm2_engine import classify_srs_mastery

    read_stmts: List[Any] = [
        ("SELECT is_pro, subscription_tier, subscription_expires_at FROM telegram_users WHERE user_id = ?", [user_id]),
        ("SELECT canonical_id FROM user_bookmarks WHERE user_id = ?", [user_id]),
    ]
    idx_ft_fin = idx_ft_unfin = idx_solved = idx_mistakes = idx_srs_all = idx_cat_perf = idx_cat_mist = -1

    if req.session_type == "EXAM":
        idx_ft_fin = len(read_stmts)
        read_stmts.append(("SELECT COUNT(*) AS cnt FROM exam_results WHERE user_id = ?", [user_id]))
        idx_ft_unfin = len(read_stmts)
        read_stmts.append((
            """
            SELECT COUNT(*) AS cnt FROM (
                SELECT us.session_id
                FROM user_sessions us
                JOIN session_answers sa ON us.session_id = sa.session_id
                LEFT JOIN exam_results er ON us.session_id = er.session_id
                WHERE us.user_id = ? AND us.session_type = 'EXAM' AND er.id IS NULL
                GROUP BY us.session_id
                HAVING COUNT(sa.id) >= 3
            )
            """.strip(),
            [user_id],
        ))
    elif req.session_type == "CATEGORY":
        if req.category_id is None:
            raise HTTPException(status_code=400, detail="category_id required for CATEGORY session")
        idx_solved = len(read_stmts)
        read_stmts.append(("SELECT DISTINCT canonical_id FROM session_answers WHERE user_id = ? AND is_correct = 1", [user_id]))
    elif req.session_type == "MISTAKES":
        limit = req.total_questions if (req.total_questions and req.total_questions > 0) else 50
        idx_mistakes = len(read_stmts)
        read_stmts.append((
            "SELECT canonical_id FROM user_mistakes WHERE user_id = ? AND is_resolved = 0 ORDER BY last_mistake_at DESC LIMIT ?",
            [user_id, limit],
        ))
    elif req.session_type in ("ADAPTIVE", "SRS"):
        idx_mistakes = len(read_stmts)
        read_stmts.append((
            "SELECT canonical_id FROM user_mistakes WHERE user_id = ? AND is_resolved = 0 ORDER BY last_mistake_at DESC LIMIT 30",
            [user_id],
        ))
        idx_solved = len(read_stmts)
        read_stmts.append(("SELECT DISTINCT canonical_id FROM session_answers WHERE user_id = ? AND is_correct = 1", [user_id]))
        idx_srs_all = len(read_stmts)
        read_stmts.append((
            """
            SELECT canonical_id, ease_factor, interval_days, repetitions, lapses, last_quality, next_review_at
            FROM user_question_srs
            WHERE user_id = ?
            ORDER BY CASE WHEN next_review_at <= ? THEN 0 ELSE 1 END ASC, next_review_at ASC, ease_factor ASC, lapses DESC
            """.strip(),
            [user_id, now_ts],
        ))
        idx_cat_perf = len(read_stmts)
        read_stmts.append((
            """
            SELECT COALESCE(cq.category_id, 0) AS category_id,
                   COUNT(sa.id) AS total_attempts,
                   COALESCE(SUM(sa.is_correct), 0) AS correct_attempts,
                   COUNT(DISTINCT sa.canonical_id) AS unique_answered,
                   COUNT(DISTINCT CASE WHEN sa.is_correct = 1 THEN sa.canonical_id END) AS unique_correct
            FROM session_answers sa
            LEFT JOIN canonical_questions cq ON sa.canonical_id = cq.canonical_id
            WHERE sa.user_id = ?
            GROUP BY COALESCE(cq.category_id, 0)
            """.strip(),
            [user_id],
        ))
        idx_cat_mist = len(read_stmts)
        read_stmts.append((
            """
            SELECT COALESCE(cq.category_id, 0) AS category_id, COUNT(*) AS active_mistakes
            FROM user_mistakes um
            LEFT JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
            WHERE um.user_id = ? AND um.is_resolved = 0
            GROUP BY COALESCE(cq.category_id, 0)
            """.strip(),
            [user_id],
        ))

    with db._get_connection() as conn:
        batches = fetch_batch_dicts(conn, read_stmts)

    user_row = batches[0][0] if batches[0] else None
    sub, _ = evaluate_subscription_row(user_row)
    bookmarks = {r["canonical_id"] for r in batches[1]}

    if req.session_type == "EXAM":
        used = (int(batches[idx_ft_fin][0]["cnt"] or 0) if batches[idx_ft_fin] else 0) + (
            int(batches[idx_ft_unfin][0]["cnt"] or 0) if batches[idx_ft_unfin] else 0
        )
        if not compute_free_tier_from_counts(sub, used)["has_access"]:
            raise HTTPException(status_code=403, detail="SUBSCRIPTION_REQUIRED")
    elif req.session_type == "CUSTOM" and req.total_questions and req.total_questions > 20:
        if not sub.get("is_pro"):
            raise HTTPException(status_code=403, detail="SUBSCRIPTION_REQUIRED")

    question_ids: List[str] = []
    loaded_questions: List[QuestionItem] = []
    queue_breakdown: Optional[Dict[str, int]] = None
    srs_map: Dict[str, Dict[str, Any]] = {}

    if req.session_type == "EXAM":
        session_data = engine.create_exam_session(language=lang)
        loaded_questions = session_data["questions"]
        question_ids = [q.canonical_id for q in loaded_questions]
        time_limit = req.time_limit_seconds if req.time_limit_seconds is not None else (25 * 60)
    elif req.session_type == "CATEGORY":
        solved_ok = {r["canonical_id"] for r in batches[idx_solved]}
        loaded_questions = engine.get_questions_by_category(
            req.category_id,
            language=lang,
            limit=req.total_questions,
            solved_ids=solved_ok,
            offset=max(0, int(req.offset or 0)),
        )
        question_ids = [q.canonical_id for q in loaded_questions]
        time_limit = req.time_limit_seconds or 0
    elif req.session_type == "MISTAKES":
        mistake_qids = [r["canonical_id"] for r in batches[idx_mistakes]]
        if not mistake_qids:
            raise HTTPException(status_code=400, detail="Xatolar banki bo‘sh. Hali xatolar mavjud emas.")
        question_ids = mistake_qids
        loaded_questions = [q for q in (engine.get_question(qid, language=lang) for qid in question_ids) if q]
        time_limit = 0
    elif req.session_type == "BILET":
        t_num = req.ticket_number if req.ticket_number is not None else req.category_id
        if t_num is None or int(t_num) < 1:
            raise HTTPException(status_code=400, detail="ticket_number required for BILET session")
        t_num = int(t_num)
        loaded_questions = engine.get_ticket_questions(t_num, language=lang)
        if not loaded_questions:
            raise HTTPException(status_code=404, detail=f"Bilet #{t_num} not found")
        question_ids = [q.canonical_id for q in loaded_questions]
        req.category_id = t_num
        time_limit = req.time_limit_seconds or 0
    elif req.session_type in ("ADAPTIVE", "SRS"):
        count = max(5, min(40, int(req.total_questions or 20)))
        unresolved = [r["canonical_id"] for r in batches[idx_mistakes]]
        solved_ok = {r["canonical_id"] for r in batches[idx_solved]}
        due_srs_ids: List[str] = []
        full_srs_map: Dict[str, Dict[str, Any]] = {}
        for r in batches[idx_srs_all]:
            cid = r["canonical_id"]
            nra = str(r["next_review_at"])
            is_due = nra <= now_ts
            if is_due:
                due_srs_ids.append(cid)
            ef = round(float(r.get("ease_factor") or 2.5), 2)
            iv = int(r.get("interval_days") or 0)
            reps = int(r.get("repetitions") or 0)
            lapses = int(r.get("lapses") or 0)
            full_srs_map[cid] = {
                "ease_factor": ef,
                "interval_days": iv,
                "repetitions": reps,
                "lapses": lapses,
                "last_quality": int(r.get("last_quality") or 0),
                "next_review_at": nra,
                "is_due": is_due,
                "mastery_level": classify_srs_mastery(reps, iv, ef, lapses),
            }
        analytics = db.analytics._assemble_analytics_payload(
            categories=engine.get_categories(lang),
            cat_perf_rows=batches[idx_cat_perf],
            cat_mistakes_rows=batches[idx_cat_mist],
            scalar_row={},
            srs_agg={"due_now_count": len(due_srs_ids), "mastered_count": 0},
            streak_val=0,
            engine_total_questions=engine.get_total_question_count(),
        )
        weak_cat_ids = [w["category_id"] for w in analytics.get("weak_categories", [])]
        if req.session_type == "SRS":
            question_ids, queue_breakdown = engine.get_srs_session_question_ids(
                count=count,
                due_srs_ids=due_srs_ids,
                unresolved_mistakes=unresolved,
                weak_category_ids=weak_cat_ids,
                solved_correct_ids=solved_ok,
            )
        else:
            question_ids = engine.get_adaptive_question_ids(
                count=count,
                unresolved_mistakes=unresolved,
                weak_category_ids=weak_cat_ids,
                solved_correct_ids=solved_ok,
                due_srs_ids=due_srs_ids,
            )
        loaded_questions = [q for q in (engine.get_question(qid, language=lang) for qid in question_ids) if q]
        srs_map = {qid: full_srs_map[qid] for qid in question_ids if qid in full_srs_map}
        time_limit = req.time_limit_seconds or 0
    else:  # RANDOM / CUSTOM
        count = max(5, min(100, int(req.total_questions or 10)))
        if req.category_id:
            import random
            cat_questions = engine.get_questions_by_category(
                int(req.category_id),
                language=lang,
                limit=1000,
            )
            if len(cat_questions) > count:
                loaded_questions = random.sample(cat_questions, count)
            else:
                loaded_questions = cat_questions
            question_ids = [q.canonical_id for q in loaded_questions]
        else:
            loaded_questions = engine.get_random_practice(count=count, language=lang)
            question_ids = [q.canonical_id for q in loaded_questions]
        time_limit = req.time_limit_seconds or 0

    if not question_ids:
        raise HTTPException(status_code=400, detail="No questions available for this configuration")

    # Create session record + log QUIZ_STARTED atomically in 1 write RT (<= 2 RTs total!)
    show_explanation = False if req.session_type == "EXAM" else (req.show_explanation if req.show_explanation is not None else True)
    session_info = db.create_session(
        user_id=user_id,
        session_type=req.session_type,
        language=lang,
        question_ids=question_ids,
        time_limit_seconds=time_limit,
        category_id=req.category_id,
        show_answer=req.show_answer if req.show_answer is not None else True,
        show_explanation=show_explanation,
        preloaded_bookmarks=bookmarks,
        log_event_data={"session_type": req.session_type, "count": len(loaded_questions)},
    )

    reveal_correct_upfront = req.session_type != "EXAM"
    questions_list = []
    for q in loaded_questions:
        if not q:
            continue
        item = serialize_question(q, is_bookmarked=(q.canonical_id in bookmarks), include_correct=reveal_correct_upfront)
        if q.canonical_id in srs_map:
            item["srs_meta"] = srs_map[q.canonical_id]
        questions_list.append(item)

    payload: Dict[str, Any] = {
        "session_id": session_info["session_id"],
        "session_type": req.session_type,
        "language": lang,
        "time_limit_seconds": time_limit,
        "total_questions": len(questions_list),
        "questions": questions_list,
        "show_answer": session_info["show_answer"],
        "show_explanation": session_info["show_explanation"],
    }
    if queue_breakdown is not None:
        payload["queue_breakdown"] = queue_breakdown
    return payload

# 4. Submit Answer
class SubmitAnswerRequest(BaseModel):
    session_id: str
    canonical_id: str
    selected_key: str
    language: Optional[str] = None
    response_time_ms: Optional[int] = Field(None, ge=0, le=3600000)
    quality: Optional[int] = Field(None, ge=0, le=5)

@router.post("/session/answer")
def submit_answer(
    req: SubmitAnswerRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    try:
        out = db.submit_session_answer_verified(
            session_id=req.session_id,
            user_id=user_id,
            canonical_id=req.canonical_id,
            selected_key=req.selected_key,
            answer_checker=lambda qid, skey, qlang: engine.check_answer(qid, skey, language=qlang),
            requested_lang=req.language,
            response_time_ms=req.response_time_ms,
            quality=req.quality,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    err = out.get("error")
    if err == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Session not found")
    if err == "FORBIDDEN":
        raise HTTPException(status_code=403, detail="Forbidden: Session belongs to another user")

    if out.get("early_terminated"):
        return {
            "canonical_id": req.canonical_id,
            "selected_key": req.selected_key.upper(),
            "correct_key": "",
            "is_correct": False,
            "explanation": "",
            "legal_reference": "",
            "streak": {"current_streak": 0, "today_questions_count": 0},
            "is_exam_terminated": True,
            "srs": None,
        }

    feedback = out["feedback"]
    res = out["result"]
    return {
        "canonical_id": req.canonical_id,
        "selected_key": req.selected_key.upper(),
        "correct_key": feedback.correct_key,
        "is_correct": feedback.is_correct,
        "explanation": feedback.explanation,
        "legal_reference": feedback.legal_reference,
        "legal_verification_status": getattr(feedback, "legal_verification_status", None),
        "legal_chapter": getattr(feedback, "legal_chapter", None),
        "legal_clause": getattr(feedback, "legal_clause", None),
        "legal_doc_title": getattr(feedback, "legal_doc_title", None),
        "streak": res["streak"],
        "is_exam_terminated": res["is_exam_terminated"],
        "srs": res.get("srs"),
    }

# 5. Finish Session & Calculate Score
class FinishSessionRequest(BaseModel):
    session_id: str
    time_elapsed_seconds: Optional[float] = 0.0

@router.post("/session/finish")
def finish_session(
    req: FinishSessionRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    bundle = db.get_session_finish_bundle(req.session_id, user_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    session = bundle["session"]
    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Session belongs to another user")

    answers = bundle["answers"]
    total_q = session["total_questions"]
    answered_count = len(answers)
    correct_count = sum(1 for a in answers.values() if a["is_correct"])
    incorrect_count = sum(1 for a in answers.values() if not a["is_correct"])
    unanswered_count = max(0, total_q - (correct_count + incorrect_count))

    percentage = round((correct_count / total_q * 100), 1) if total_q > 0 else 0.0
    is_exam = (session["session_type"] == "EXAM")
    # DYHXX VMQ 408 rule: 18+ correct AND at most 2 mistakes (3 mistakes = immediate fail)
    passed = (correct_count >= 18 and incorrect_count <= 2) if is_exam else (percentage >= 80.0)

    # Category breakdown (in-memory catalog lookup -> 0 DB RTs!)
    lang = session["language"]
    category_breakdown: Dict[str, Dict[str, int]] = {}
    for qid, ans in answers.items():
        q = engine.get_question(qid, language=lang)
        cat_name = q.category_name if q else "Boshqa"
        if cat_name not in category_breakdown:
            category_breakdown[cat_name] = {"correct": 0, "incorrect": 0, "total": 0}
        category_breakdown[cat_name]["total"] += 1
        if ans["is_correct"]:
            category_breakdown[cat_name]["correct"] += 1
        else:
            category_breakdown[cat_name]["incorrect"] += 1

    # Save exam result record + ticket progress + finish session atomically in 1 single write batch!
    finish_status = "FAILED_MISTAKES" if (is_exam and incorrect_count > 2) else "COMPLETED"
    ticket_num = int(session["category_id"]) if (session.get("session_type") == "BILET" and session.get("category_id")) else None
    db.finalize_exam_session(
        session_id=req.session_id,
        user_id=user_id,
        total_q=total_q,
        correct=correct_count,
        incorrect=incorrect_count,
        pct=percentage,
        passed=passed,
        time_spent=req.time_elapsed_seconds or 0.0,
        category_breakdown=category_breakdown,
        unanswered=unanswered_count,
        status=finish_status,
        record_exam_result=is_exam,
        ticket_number=ticket_num,
    )

    invalidate_auth_cache(user_id)

    return {
        "session_id": req.session_id,
        "session_type": session["session_type"],
        "total_questions": total_q,
        "answered_count": answered_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unanswered_count": unanswered_count,
        "percentage": percentage,
        "passed": passed,
        "time_elapsed_seconds": req.time_elapsed_seconds,
        "category_breakdown": category_breakdown,
        "terminated_reason": "MAX_MISTAKES_EXCEEDED" if (is_exam and incorrect_count > 2) else None
    }

# 6. Get Existing Session State
@router.get("/session/{session_id}")
def get_session_state(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: Session belongs to another user")

    answers = db.get_session_answers(session_id)
    return {
        "session": session,
        "answers": answers
    }

# 7. Bookmarks
@router.get("/bookmarks")
def list_bookmarks(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    selected_lang = lang or user.get("language", "uz_latn")
    bookmark_ids = db.get_user_bookmarks(user_id)
    
    questions = []
    for qid in bookmark_ids:
        q = engine.get_question(qid, language=selected_lang, include_answer_key=True)
        if q:
            questions.append(serialize_question(q, is_bookmarked=True, include_correct=True))

    return {
        "count": len(questions),
        "questions": questions
    }

class BookmarkToggleRequest(BaseModel):
    canonical_id: str

@router.post("/bookmarks/toggle")
def toggle_bookmark(
    req: BookmarkToggleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    is_bm = db.toggle_bookmark(user["user_id"], req.canonical_id)
    return {"ok": True, "canonical_id": req.canonical_id, "is_bookmarked": is_bm}

# 8. User Mistakes Pool
@router.get("/mistakes")
def list_mistakes(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    selected_lang = lang or user.get("language", "uz_latn")
    mistake_ids = db.get_user_mistakes(user_id, limit=50)
    sub = db.get_user_subscription(user_id)
    is_pro = sub.get("is_pro", False)

    questions = []
    if is_pro:
        bookmarks_set = set(db.get_user_bookmarks(user_id))
        for qid in mistake_ids:
            q = engine.get_question(qid, language=selected_lang, include_answer_key=True)
            if q:
                questions.append(serialize_question(q, is_bookmarked=(qid in bookmarks_set), include_correct=True))

    return {
        "count": len(mistake_ids),
        "locked": not is_pro,
        "questions": questions
    }

# 9. RULLY 2.0 Systematic Tickets (Bilet 01..67)
@router.get("/tickets")
def list_tickets(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    selected_lang = lang or user.get("language", "uz_latn")
    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"

    summary = engine.get_tickets_summary(language=selected_lang)
    progress_map = db.get_ticket_progress_map(user["user_id"])

    passed_tickets = 0
    attempted_tickets = 0
    tickets_out = []
    for item in summary:
        t_num = item["ticket_number"]
        prog = progress_map.get(t_num)
        if prog:
            attempted_tickets += 1
            if prog["is_passed"]:
                passed_tickets += 1
        tickets_out.append({
            **item,
            "attempts_count": prog["attempts_count"] if prog else 0,
            "best_correct": prog["best_correct"] if prog else 0,
            "best_percentage": prog["best_percentage"] if prog else 0.0,
            "is_passed": prog["is_passed"] if prog else False,
            "last_session_id": prog["last_session_id"] if prog else None,
        })

    return {
        "language": selected_lang,
        "total_tickets": len(tickets_out),
        "attempted_tickets": attempted_tickets,
        "passed_tickets": passed_tickets,
        "tickets": tickets_out
    }

# 10. RULLY 2.0 Learning Analytics, Category Mastery, Smart Next Action & Milestones
@router.get("/learning/analytics")
def get_learning_analytics_endpoint(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    selected_lang = lang or user.get("language", "uz_latn")
    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"

    categories = engine.get_categories(selected_lang)
    analytics = db.get_learning_analytics(
        user_id=user["user_id"],
        categories=categories,
        engine_total_questions=engine.get_total_question_count(),
    )
    return {
        "ok": True,
        "language": selected_lang,
        **analytics
    }

# 11. RULLY 2.0 Post-Session Detailed Review
@router.get("/session/{session_id}/review")
def get_session_review_endpoint(
    session_id: str,
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    bundle = db.get_session_review(session_id, user["user_id"])
    if not bundle:
        raise HTTPException(status_code=404, detail="Session not found")
    if bundle.get("forbidden"):
        raise HTTPException(status_code=403, detail="Forbidden: Session belongs to another user")

    session = bundle["session"]
    selected_lang = lang or session.get("language") or user.get("language", "uz_latn")
    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"

    answers = bundle["answers"]
    bookmarks = bundle["bookmarks"]
    items = []
    for idx, qid in enumerate(session["question_ids"], start=1):
        q = engine.get_question(qid, language=selected_lang, include_answer_key=True)
        if not q:
            continue
        ans = answers.get(qid)
        serialized = serialize_question(q, is_bookmarked=(qid in bookmarks), include_correct=True)
        items.append({
            "index": idx,
            "selected_key": ans["selected_key"] if ans else None,
            "is_correct": ans["is_correct"] if ans else None,
            "answered_at": ans["answered_at"] if ans else None,
            **serialized,
        })

    return {
        "ok": True,
        "session_id": session_id,
        "session_type": session.get("session_type"),
        "ticket_number": session.get("category_id") if session.get("session_type") == "BILET" else None,
        "status": session.get("status"),
        "total_questions": session.get("total_questions"),
        "correct_count": session.get("correct_count"),
        "incorrect_count": session.get("incorrect_count"),
        "items": items
    }


# 12. RULLY 2.0 Statutory Road Signs Explorer & VMQ 172 Law Reader
@router.get("/reference/signs")
def get_reference_signs_endpoint(
    response: Response,
    lang: Optional[str] = Query("uz_latn"),
):
    selected_lang = lang if lang in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=3600"
    return get_road_signs_reference(selected_lang)


@router.get("/reference/law")
def get_reference_law_endpoint(
    response: Response,
    lang: Optional[str] = Query("uz_latn"),
):
    selected_lang = lang if lang in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=3600"
    return get_law_reference(selected_lang)


# 13. RULLY 2.0 Phase 5 — SM-2 Spaced Repetition Daily Queue ("Aqlli Takrorlash")
class SrsReviewRequest(BaseModel):
    canonical_id: str
    quality: int = Field(..., ge=0, le=5)
    recalibrate: bool = False


@router.get("/srs/queue")
def get_srs_queue_endpoint(
    lang: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db),
):
    selected_lang = lang or user.get("language", "uz_latn")
    if selected_lang not in ("uz_latn", "uz_cyrl", "ru"):
        selected_lang = "uz_latn"

    user_id = user["user_id"]
    queue = db.get_srs_queue_summary(
        user_id=user_id,
        total_bank_questions=engine.get_total_question_count(),
        limit=limit,
    )
    enriched_items = []
    for row in queue["items"]:
        q = engine.get_question(row["canonical_id"], language=selected_lang)
        enriched_items.append({
            **row,
            "question_text": q.question_text if q else "",
            "category_id": q.category_id if q else None,
            "category_name": q.category_name if q else "",
            "has_image": bool(q and q.has_image),
        })

    return {
        "ok": True,
        "language": selected_lang,
        "summary": queue["summary"],
        "due_question_ids": queue["due_question_ids"],
        "items": enriched_items,
    }


@router.post("/srs/review")
def submit_srs_review_endpoint(
    req: SrsReviewRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db),
):
    q = engine.get_question(req.canonical_id, language=user.get("language", "uz_latn"))
    if not q:
        raise HTTPException(status_code=404, detail="Canonical question not found")

    user_id = user["user_id"]
    srs_state = db.record_srs_review(
        user_id=user_id,
        canonical_id=req.canonical_id,
        quality=req.quality,
        recalibrate=req.recalibrate,
    )
    invalidate_auth_cache(user_id)
    return {
        "ok": True,
        "canonical_id": req.canonical_id,
        "srs": srs_state,
    }


# 14. Public Freemium Web Preview (Anonymous 60-Second Diagnostic + Catalog Overview)
class PublicDiagnosticAnswer(BaseModel):
    canonical_id: str
    selected_key: str


class PublicDiagnosticCheckRequest(BaseModel):
    language: Optional[str] = "uz_latn"
    answers: List[PublicDiagnosticAnswer] = Field(..., min_length=1, max_length=10)


@router.get("/public/overview")
def get_public_freemium_overview(
    request: Request,
    response: Response,
    lang: Optional[str] = Query("uz_latn"),
):
    ip = get_client_ip(request)
    allowed, _, retry_after = rate_limiter.is_allowed(f"pub_ov:{ip}", max_requests=40, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many requests. Wait {int(retry_after)}s.")

    selected_lang = lang if lang in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    cats = engine.get_categories(selected_lang)

    # Pick 5 deterministic representative diagnostic questions across diverse categories (images first when present)
    engine.ensure_fresh_cache()
    picked = []
    used_cats = set()
    all_ids = list(engine._all_canonical_ids or [])
    for cid in all_ids:
        q = engine.get_question(cid, language=selected_lang, include_answer_key=False)
        if not q or q.category_id in used_cats:
            continue
        if len(picked) < 3 and not q.has_image:
            continue
        picked.append(serialize_question(q, is_bookmarked=False, include_correct=False))
        used_cats.add(q.category_id)
        if len(picked) >= 5:
            break
    if len(picked) < 5:
        for cid in all_ids:
            if any(p["canonical_id"] == cid for p in picked):
                continue
            q = engine.get_question(cid, language=selected_lang, include_answer_key=False)
            if q:
                picked.append(serialize_question(q, is_bookmarked=False, include_correct=False))
            if len(picked) >= 5:
                break

    response.headers["Cache-Control"] = "public, max-age=120, s-maxage=600"
    return {
        "ok": True,
        "language": selected_lang,
        "total_questions": engine.get_total_question_count(),
        "total_categories": len(cats),
        "categories": cats,
        "diagnostic_questions": picked,
    }


@router.post("/public/diagnostic/check")
def check_public_diagnostic(
    req: PublicDiagnosticCheckRequest,
    request: Request,
):
    ip = get_client_ip(request)
    allowed, _, retry_after = rate_limiter.is_allowed(f"pub_chk:{ip}", max_requests=30, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many requests. Wait {int(retry_after)}s.")

    selected_lang = req.language if req.language in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    items = []
    correct_count = 0
    for ans in req.answers[:10]:
        fb = engine.check_answer(ans.canonical_id, ans.selected_key, language=selected_lang)
        if not fb:
            continue
        if fb.is_correct:
            correct_count += 1
        items.append({
            "canonical_id": fb.canonical_id,
            "is_correct": fb.is_correct,
            "selected_key": ans.selected_key.strip().upper(),
            "correct_option_key": fb.correct_key,
            "explanation": fb.explanation,
            "legal_reference": fb.legal_reference,
        })

    total = max(1, len(items))
    pct = round((correct_count / total) * 100, 1)
    return {
        "ok": True,
        "correct_count": correct_count,
        "total": len(items),
        "percentage": pct,
        "items": items,
    }

