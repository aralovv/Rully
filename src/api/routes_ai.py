import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.db_adapter import get_db_connection
from src.ai.gemini_service import GeminiService

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])
gemini_service = GeminiService()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "uz_latn"

class ClearHistoryRequest(BaseModel):
    session_id: Optional[str] = "default"

@router.get("/status")
async def get_ai_status(
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    sub = db.get_user_subscription(user_id)
    is_pro = sub.get("is_pro", False)

    # Check today's usage
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    SELECT request_count FROM ai_usage_limits
    WHERE user_id = ? AND usage_date = DATE('now')
    """, (user_id,))
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
            "remaining": max(0, max_limit - current) if is_pro else 0
        }
    }

@router.post("/chat")
async def chat_with_ai(
    req: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    sub = db.get_user_subscription(user_id)
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

    msg = req.message.strip()
    if not msg:
        empty_reply = "Iltimos, savolingizni yozing." if lang == "uz_latn" else ("Илтимос, саволингизни ёзинг." if lang == "uz_cyrl" else "Пожалуйста, введите ваш вопрос.")
        return {"ok": False, "reply": empty_reply}

    session_id = req.session_id or "default"
    result = await gemini_service.chat(
        user_id=user_id,
        session_id=session_id,
        message=msg,
        is_pro=is_pro,
        language=lang
    )
    return result

@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = Query("default"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = user["user_id"]
    history = gemini_service.get_conversation_history(user_id, session_id or "default", limit=20)
    
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

@router.post("/clear")
async def clear_chat_history(
    req: ClearHistoryRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = user["user_id"]
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    DELETE FROM ai_conversations
    WHERE user_id = ? AND session_id = ?
    """, (user_id, req.session_id or "default"))
    conn.commit()
    return {"ok": True, "cleared": True}
