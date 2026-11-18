"""
Theory Exam and Category Practice API endpoints for RULLY Mini App.
"""

import os
import json
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine, QuestionItem
from src.bot.category_localization import localize_category

router = APIRouter(prefix="/api", tags=["Theory & Exam"])
engine = AvtotestProductEngine("master_database.sqlite")

def serialize_question(q: QuestionItem, is_bookmarked: bool = False, include_correct: bool = False) -> Dict[str, Any]:
    image_url = None
    if q.has_image and q.image_path:
        filename = os.path.basename(q.image_path.replace("\\", "/"))
        image_url = f"/images/{filename}"

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
        "explanation": q.explanation if include_correct else None,
        "correct_option_key": q.correct_option_key if include_correct else None,
        "correct_answer_text": correct_answer_text,
        "is_bookmarked": is_bookmarked
    }

# 1. Categories
@router.get("/categories")
async def list_categories(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    selected_lang = lang or user.get("language", "uz_latn")
    if selected_lang not in ["uz_latn", "uz_cyrl", "ru"]:
        selected_lang = "uz_latn"
    
    categories = engine.get_categories(selected_lang)
    return {
        "language": selected_lang,
        "count": len(categories),
        "categories": categories
    }

# 2. Get Single Question
@router.get("/questions/{canonical_id}")
async def get_question(
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

# 3. Start Session (Exam, Category, Random, Mistakes)
class SessionStartRequest(BaseModel):
    session_type: str = Field(..., pattern="^(EXAM|CATEGORY|RANDOM|MISTAKES|CUSTOM)$")
    category_id: Optional[int] = None
    total_questions: Optional[int] = 20
    time_limit_seconds: Optional[int] = 25 * 60
    show_answer: Optional[bool] = True
    show_explanation: Optional[bool] = True
    language: Optional[str] = None

@router.post("/session/start")
async def start_session(
    req: SessionStartRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    lang = req.language or user.get("language", "uz_latn")
    if lang not in ["uz_latn", "uz_cyrl", "ru"]:
        lang = "uz_latn"

    # Enforce PRO subscription for State Exam, Mistakes Bank, and Extended Custom Quiz (> 20 questions)
    if req.session_type in ["EXAM", "MISTAKES"] or (req.session_type == "CUSTOM" and req.total_questions and req.total_questions > 20):
        sub = db.get_user_subscription(user_id)
        if not sub.get("is_pro"):
            raise HTTPException(
                status_code=403,
                detail="SUBSCRIPTION_REQUIRED"
            )

    # Select questions according to session type
    question_ids: List[str] = []
    if req.session_type == "EXAM":
        # 20 questions, 25 minutes standard
        session_data = engine.create_exam_session(language=lang)
        question_ids = [q.canonical_id for q in session_data["questions"]]
        time_limit = req.time_limit_seconds if req.time_limit_seconds is not None else (25 * 60)
    elif req.session_type == "CATEGORY":
        if req.category_id is None:
            raise HTTPException(status_code=400, detail="category_id required for CATEGORY session")
        questions = engine.get_questions_by_category(req.category_id, language=lang, limit=req.total_questions)
        question_ids = [q.canonical_id for q in questions]
        time_limit = req.time_limit_seconds or 0
    elif req.session_type == "MISTAKES":
        limit = req.total_questions if (req.total_questions and req.total_questions > 0) else 50
        mistake_qids = db.get_user_mistakes(user_id, limit=limit)
        if not mistake_qids:
            raise HTTPException(
                status_code=400,
                detail="Xatolar banki bo‘sh. Hali xatolar mavjud emas."
            )
        question_ids = mistake_qids
        time_limit = 0
    else:  # RANDOM / CUSTOM
        count = req.total_questions or 10
        random_qs = engine.get_random_practice(count=count, language=lang)
        question_ids = [q.canonical_id for q in random_qs]
        time_limit = req.time_limit_seconds or 0

    if not question_ids:
        raise HTTPException(status_code=400, detail="No questions available for this configuration")

    # Create session record
    show_explanation = False if req.session_type == "EXAM" else (req.show_explanation if req.show_explanation is not None else True)
    session_info = db.create_session(
        user_id=user_id,
        session_type=req.session_type,
        language=lang,
        question_ids=question_ids,
        time_limit_seconds=time_limit,
        category_id=req.category_id,
        show_answer=req.show_answer if req.show_answer is not None else True,
        show_explanation=show_explanation
    )

    # Fetch serialized question objects
    bookmarks = set(db.get_user_bookmarks(user_id))
    questions_list = []
    for qid in question_ids:
        q = engine.get_question(qid, language=lang)
        if q:
            questions_list.append(serialize_question(q, is_bookmarked=(qid in bookmarks), include_correct=False))

    return {
        "session_id": session_info["session_id"],
        "session_type": req.session_type,
        "language": lang,
        "time_limit_seconds": time_limit,
        "total_questions": len(questions_list),
        "questions": questions_list,
        "show_answer": session_info["show_answer"],
        "show_explanation": session_info["show_explanation"]
    }

# 4. Submit Answer
class SubmitAnswerRequest(BaseModel):
    session_id: str
    canonical_id: str
    selected_key: str
    language: Optional[str] = None

@router.post("/session/answer")
async def submit_answer(
    req: SubmitAnswerRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    session = db.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = req.language or session.get("language", "uz_latn")
    try:
        feedback = engine.check_answer(req.canonical_id, req.selected_key, language=lang)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Record in session_answers (idempotent)
    db.save_answer(
        session_id=req.session_id,
        canonical_id=req.canonical_id,
        selected_key=req.selected_key.upper(),
        correct_key=feedback.correct_key,
        is_correct=feedback.is_correct
    )

    # Track mistake pool
    if not feedback.is_correct:
        db.record_mistake(user_id, req.canonical_id)
    else:
        db.resolve_mistake(user_id, req.canonical_id)

    # Increment learning streak
    streak = db.increment_streak_progress(user_id, 1)

    return {
        "canonical_id": req.canonical_id,
        "selected_key": req.selected_key.upper(),
        "correct_key": feedback.correct_key,
        "is_correct": feedback.is_correct,
        "explanation": feedback.explanation,
        "legal_reference": feedback.legal_reference,
        "streak": streak
    }

# 5. Finish Session & Calculate Score
class FinishSessionRequest(BaseModel):
    session_id: str
    time_elapsed_seconds: Optional[float] = 0.0

@router.post("/session/finish")
async def finish_session(
    req: FinishSessionRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    session = db.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers = db.get_session_answers(req.session_id)
    total_q = session["total_questions"]
    answered_count = len(answers)
    correct_count = sum(1 for a in answers.values() if a["is_correct"])
    incorrect_count = sum(1 for a in answers.values() if not a["is_correct"])
    unanswered_count = max(0, total_q - (correct_count + incorrect_count))

    percentage = round((correct_count / total_q * 100), 1) if total_q > 0 else 0.0
    passed = (correct_count >= 18) if session["session_type"] == "EXAM" else (percentage >= 80.0)

    # Category breakdown
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

    # Save exam result record if EXAM or graded practice
    db.save_exam_result(
        session_id=req.session_id,
        user_id=user_id,
        total_q=total_q,
        correct=correct_count,
        incorrect=incorrect_count,
        pct=percentage,
        passed=passed,
        time_spent=req.time_elapsed_seconds or 0.0,
        category_breakdown=category_breakdown,
        unanswered=unanswered_count
    )

    db.finish_session(req.session_id, status="COMPLETED")

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
        "category_breakdown": category_breakdown
    }

# 6. Get Existing Session State
@router.get("/session/{session_id}")
async def get_session_state(
    session_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers = db.get_session_answers(session_id)
    return {
        "session": session,
        "answers": answers
    }

# 7. Bookmarks
@router.get("/bookmarks")
async def list_bookmarks(
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
async def toggle_bookmark(
    req: BookmarkToggleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    is_bm = db.toggle_bookmark(user["user_id"], req.canonical_id)
    return {"ok": True, "canonical_id": req.canonical_id, "is_bookmarked": is_bm}

# 8. User Mistakes Pool
@router.get("/mistakes")
async def list_mistakes(
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
        for qid in mistake_ids:
            q = engine.get_question(qid, language=selected_lang, include_answer_key=True)
            if q:
                questions.append(serialize_question(q, is_bookmarked=db.is_bookmarked(user_id, qid), include_correct=True))

    return {
        "count": len(mistake_ids),
        "locked": not is_pro,
        "questions": questions
    }
