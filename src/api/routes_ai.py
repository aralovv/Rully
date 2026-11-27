import asyncio
import json
import os
import re
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.db_adapter import get_db_connection
from src.ai.gemini_service import GeminiService
from src.db.tz_utils import tashkent_today_str
from src.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])
gemini_service = GeminiService()

def _clean_session_id(raw_sid: Optional[str]) -> str:
    sid = str(raw_sid or "default").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,64}", sid):
        return "default"
    return sid


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: Optional[str] = "default"
    language: Optional[str] = "uz_latn"
    image_url: Optional[str] = Field(None, max_length=512)
    canonical_id: Optional[str] = Field(None, max_length=64)
    question_context: Optional[Dict[str, Any]] = None

class ClearHistoryRequest(BaseModel):
    session_id: Optional[str] = "default"

def _load_ai_status_sync(db: BotDatabase, user_id: int) -> Dict[str, Any]:
    sub = db.get_user_subscription(user_id)
    is_pro = sub.get("is_pro", False)
    today = tashkent_today_str()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT request_count FROM ai_usage_limits
            WHERE user_id = ? AND usage_date = ?
            """,
            (user_id, today),
        )
        row = c.fetchone()
        current = row["request_count"] if row else 0
        max_limit = 100 if is_pro else 3
    return {
        "ok": True,
        "is_pro": is_pro,
        "free_teaser_daily": 3,
        "locked": (not is_pro) and (current >= max_limit),
        "requires_pro": (not is_pro) and (current >= max_limit),
        "has_api_key": bool(gemini_service.api_key),
        "usage": {
            "current": current,
            "max": max_limit,
            "remaining": max(0, max_limit - current),
        },
    }

@router.get("/status")
async def get_ai_status(
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    return await asyncio.to_thread(_load_ai_status_sync, db, user["user_id"])

@router.post("/chat")
async def chat_with_ai(
    req: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    sub = await asyncio.to_thread(db.get_user_subscription, user_id)
    is_pro = sub.get("is_pro", False)
    lang = req.language or user.get("language") or "uz_latn"

    # Rate limit (P0): max 5 requests per minute per user (RPM protection)
    allowed, _, retry_after = rate_limiter.is_allowed(f"ai_rpm:{user_id}", max_requests=5, window_seconds=60)
    if not allowed:
        rpm_msg = (
            f"Iltimos, biroz kuting. AI Ustozga minutiga ko‘pi bilan 5 ta so‘rov yuborish mumkin ({int(retry_after)} soniya kuting)."
            if lang == "uz_latn" else (
                f"Илтимос, бироз кутинг. AI Устозга минутига кўпи билан 5 та сўров юбориш мумкин ({int(retry_after)} сония кутинг)."
                if lang == "uz_cyrl" else
                f"Пожалуйста, подождите. К AI можно отправлять не более 5 запросов в минуту (подождите {int(retry_after)} сек)."
            )
        )
        return {
            "ok": False,
            "reply": rpm_msg,
            "rate_limited": True,
            "retry_after": retry_after
        }

    msg = req.message.strip()
    if not msg:
        empty_reply = "Iltimos, savolingizni yozing." if lang == "uz_latn" else ("Илтимос, саволингизни ёзинг." if lang == "uz_cyrl" else "Пожалуйста, введите ваш вопрос.")
        return {"ok": False, "reply": empty_reply}

    session_id = _clean_session_id(req.session_id)
    student_snapshot = await asyncio.to_thread(db.get_ai_student_snapshot, user_id)
    result = await gemini_service.chat(
        user_id=user_id,
        session_id=session_id,
        message=msg,
        is_pro=is_pro,
        language=lang,
        image_url=req.image_url,
        canonical_id=req.canonical_id,
        question_context=req.question_context,
        student_snapshot=student_snapshot,
    )
    return result


@router.post("/chat/stream")
async def stream_chat_with_ai(
    req: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db),
):
    user_id = user["user_id"]
    sub = await asyncio.to_thread(db.get_user_subscription, user_id)
    is_pro = sub.get("is_pro", False)
    lang = req.language or user.get("language") or "uz_latn"
    msg = req.message.strip()
    if not msg:
        empty_err = (
            "Пожалуйста, введите ваш вопрос."
            if lang == "ru"
            else (
                "Илтимос, саволингизни ёзинг."
                if lang == "uz_cyrl"
                else "Iltimos, savolingizni yozing."
            )
        )
        async def _empty_stream():
            yield f"data: {json.dumps({'type': 'error', 'reply': empty_err, 'detail': empty_err, 'message': empty_err}, ensure_ascii=False)}\n\n"
        return StreamingResponse(_empty_stream(), media_type="text/event-stream")

    allowed, _, retry_after = rate_limiter.is_allowed(f"ai_rpm:{user_id}", max_requests=5, window_seconds=60)
    if not allowed:
        rate_msg = (
            f"Слишком много запросов. Повторите через {int(retry_after)} сек."
            if lang == "ru"
            else (
                f"Сўровлар жуда тез юборилмоқда. {int(retry_after)} сониядан сўнг қайта уриниб кўринг."
                if lang == "uz_cyrl"
                else f"So'rovlar juda tez yuborilmoqda. {int(retry_after)} soniyadan so'ng qayta urinib ko'ring."
            )
        )
        async def _rate_err():
            yield f"data: {json.dumps({'type': 'error', 'rate_limited': True, 'retry_after': int(retry_after), 'reply': rate_msg, 'detail': rate_msg, 'message': rate_msg}, ensure_ascii=False)}\n\n"
        return StreamingResponse(_rate_err(), media_type="text/event-stream")

    student_snapshot = await asyncio.to_thread(db.get_ai_student_snapshot, user_id)
    return StreamingResponse(
        gemini_service.stream_chat(
            user_id=user_id,
            session_id=_clean_session_id(req.session_id),
            message=msg,
            is_pro=is_pro,
            language=lang,
            image_url=req.image_url,
            canonical_id=req.canonical_id,
            question_context=req.question_context,
            student_snapshot=student_snapshot,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = Query("default"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = user["user_id"]
    history = await asyncio.to_thread(
        gemini_service.get_conversation_history, user_id, _clean_session_id(session_id), 20, True
    )
    return {"ok": True, "messages": history}

def _clear_history_sync(user_id: int, session_id: str) -> None:
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            DELETE FROM ai_conversations
            WHERE user_id = ? AND session_id = ?
            """,
            (user_id, session_id),
        )
        conn.commit()

@router.post("/clear")
async def clear_chat_history(
    req: ClearHistoryRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    await asyncio.to_thread(_clear_history_sync, user["user_id"], _clean_session_id(req.session_id))
    return {"ok": True, "cleared": True}
