import asyncio
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.db_adapter import get_db_connection
from src.ai.gemini_service import GeminiService
from src.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])
gemini_service = GeminiService()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "uz_latn"
    image_url: Optional[str] = None
    canonical_id: Optional[str] = None
    question_context: Optional[Dict[str, Any]] = None

class ClearHistoryRequest(BaseModel):
    session_id: Optional[str] = "default"

def _load_ai_status_sync(db: BotDatabase, user_id: int) -> Dict[str, Any]:
    sub = db.get_user_subscription(user_id)
    is_pro = sub.get("is_pro", False)
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT request_count FROM ai_usage_limits
            WHERE user_id = ? AND usage_date = DATE('now')
            """,
            (user_id,),
        )
        row = c.fetchone()
        current = row["request_count"] if row else 0
        max_limit = 100 if is_pro else 0
    return {
        "ok": True,
        "is_pro": is_pro,
        "locked": not is_pro,
        "requires_pro": not is_pro,
        "has_api_key": bool(gemini_service.api_key),
        "usage": {
            "current": current,
            "max": max_limit,
            "remaining": max(0, max_limit - current) if is_pro else 0,
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

    # AI Assistant is exclusively for RULLY PRO subscribers
    if not is_pro:
        pro_msg = (
            "🔒 <b>AI Ustoz faqat RULLY PRO obunasi bilan ishlaydi!</b>\n\n"
            "Yo‘l harakati qoidalari, murakkab chorrahalar va testdagi xatolaringizni sun’iy intellekt orqali chuqur tahlil qilish uchun PRO tarifni faollashtiring."
            if lang == "uz_latn" else (
                "🔒 <b>AI Устоз фақат RULLY PRO обунаси билан ишлайди!</b>\n\n"
                "Йўл ҳаракати қоидалари, мураккаб чорраҳалар ва тестдаги хатоларингизни сунъий интеллект орқали чуқур таҳлил қилиш учун PRO тарифни фаоллаштиринг."
                if lang == "uz_cyrl" else
                "🔒 <b>AI Наставник доступен только по подписке RULLY PRO!</b>\n\n"
                "Чтобы разбирать ПДД, сложные перекрёстки и ваши ошибки в тестах с помощью искусственного интеллекта, активируйте тариф PRO."
            )
        )
        return {
            "ok": False,
            "requires_pro": True,
            "reply": pro_msg
        }

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

    session_id = req.session_id or "default"
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

@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = Query("default"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = user["user_id"]
    history = await asyncio.to_thread(
        gemini_service.get_conversation_history, user_id, session_id or "default", limit=20
    )
    
    # Format for client
    formatted = []
    for item in history:
        role = "user" if item["role"] == "user" else "assistant"
        text = item["parts"][0].get("text", "")
        formatted.append({
            "role": role,
            "text": text
        })
    return {"ok": True, "messages": formatted}

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
    await asyncio.to_thread(_clear_history_sync, user["user_id"], req.session_id or "default")
    return {"ok": True, "cleared": True}
