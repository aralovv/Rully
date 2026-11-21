import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from src.ai.prompts import SYSTEM_PROMPT_UZ, get_system_prompt
from src.ai.tools import GEMINI_TOOLS_DECLARATIONS, TOOL_MAPPING, normalize_lang
from src.db_adapter import get_db_connection

logger = logging.getLogger(__name__)

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"

class GeminiService:
    def __init__(self):
        pass

    @property
    def api_key(self):
        val = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return val.strip() if val else None

    def check_and_increment_rate_limit(self, user_id: int, is_pro: bool) -> tuple[bool, int, int]:
        """
        AI Assistant is an exclusive PRO subscription feature.
        Non-PRO users: 0 requests allowed.
        PRO users: up to 100 requests per day for fair use / anti-spam protection.
        Returns: (allowed: bool, current_usage: int, max_limit: int)
        """
        if not is_pro:
            return False, 0, 0

        max_limit = 100
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Today's date in YYYY-MM-DD
            c.execute("""
            SELECT request_count FROM ai_usage_limits
            WHERE user_id = ? AND usage_date = DATE('now')
            """, (user_id,))
            row = c.fetchone()
            
            current = row["request_count"] if row else 0
            if current >= max_limit:
                return False, current, max_limit

            # Increment or insert
            c.execute("""
            INSERT INTO ai_usage_limits (user_id, usage_date, request_count)
            VALUES (?, DATE('now'), 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET request_count = request_count + 1
            """, (user_id,))
            conn.commit()
            
            return True, current + 1, max_limit

    def get_conversation_history(self, user_id: int, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                SELECT role, content FROM ai_conversations
                WHERE user_id = ? AND session_id = ?
                ORDER BY id DESC LIMIT ?
                """, (user_id, session_id, limit))
                rows = c.fetchall()
                rows.reverse() # chronological
                return [{"role": "user" if r["role"] == "user" else "model", "parts": [{"text": r["content"]}]} for r in rows]
        except Exception as e:
            logger.warning(f"Failed to fetch conversation history: {e}")
            return []

    def save_message(self, user_id: int, session_id: str, role: str, content: str, meta_json: Optional[str] = None):
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                INSERT INTO ai_conversations (user_id, session_id, role, content, meta_json)
                VALUES (?, ?, ?, ?, ?)
                """, (user_id, session_id, role, content, meta_json))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to persist AI conversation message: {e}")

    async def chat(
        self,
        user_id: int,
        session_id: str,
        message: str,
        is_pro: bool = False,
        language: str = "uz_latn"
    ) -> Dict[str, Any]:
        lang = normalize_lang(language)

        # 1. Pro Subscription Check
        if not is_pro:
            if lang == "ru":
                pro_msg = (
                    "🔒 **AI Наставник доступен только по подписке RULLY PRO!**\n\n"
                    "⚡ Подключите **PRO-подписку** для персонального автоинструктора, "
                    "разбора сложных правил, перекрёстков и анализа ваших ошибок."
                )
            elif lang == "uz_cyrl":
                pro_msg = (
                    "🔒 **AI Устоз фақат RULLY PRO обунаси билан ишлайди!**\n\n"
                    "⚡ Шахсий автоинструктор, йўл ҳаракати қоидалари таҳлили ва хатоларингизни кўриб чиқиш учун "
                    "**PRO обунани** фаоллаштиринг!"
                )
            else:
                pro_msg = (
                    "🔒 **AI Ustoz faqat RULLY PRO obunasi bilan ishlaydi!**\n\n"
                    "⚡ Shaxsiy avtoinstruktor, yo‘l harakati qoidalari tahlili va xatolaringizni ko‘rib chiqish uchun "
                    "**PRO obunani** faollashtiring!"
                )
            return {
                "ok": False,
                "requires_pro": True,
                "reply": pro_msg,
                "limit_reached": True,
                "usage": {"current": 0, "max": 0},
                "cards": []
            }

        # 2. Rate Limit Check (PRO users fair use limit)
        allowed, current_count, max_limit = self.check_and_increment_rate_limit(user_id, is_pro)
        if not allowed:
            if lang == "ru":
                limit_msg = f"Ваш дневной лимит запросов к AI ({max_limit}) исчерпан. Пожалуйста, продолжите завтра."
            elif lang == "uz_cyrl":
                limit_msg = f"Кунлик AI сўровлар лимитингиз ({max_limit} та) тугади. Илтимос, эртага давом этинг."
            else:
                limit_msg = f"Kunlik AI so‘rovlar limitingiz ({max_limit} ta) tugadi. Iltimos, ertaga davom eting."
            return {
                "ok": False,
                "reply": limit_msg,
                "limit_reached": True,
                "usage": {"current": current_count, "max": max_limit},
                "cards": []
            }

        # 2. Check API key
        if not self.api_key:
            if lang == "ru":
                reply = "⚠️ **AI Инструктор настраивается.**\n\nСервис скоро заработает в полном объеме."
            elif lang == "uz_cyrl":
                reply = "⚠️ **AI Устоз хизмати созланмоқда.**\n\nТез орада тўлиқ ишга тушади."
            else:
                reply = "⚠️ **AI Ustoz xizmati sozlanmoqda.**\n\nTez orada to'liq ishga tushadi."
            return {
                "ok": True,
                "reply": reply,
                "limit_reached": False,
                "usage": {"current": current_count, "max": max_limit},
                "cards": []
            }

        # 3. Save User Message
        self.save_message(user_id, session_id, "user", message)

        # 4. Build Gemini Payload
        history = self.get_conversation_history(user_id, session_id, limit=8)
        # Ensure latest user message is present
        if not history or history[-1]["parts"][0].get("text") != message:
            history.append({"role": "user", "parts": [{"text": message}]})

        contents = history
        tools_def = [{"function_declarations": GEMINI_TOOLS_DECLARATIONS}]
        
        system_instruction = {
            "parts": [{"text": get_system_prompt(lang)}]
        }

        url = f"{GEMINI_API_ENDPOINT}?key={self.api_key}"
        req_headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        payload = {
            "system_instruction": system_instruction,
            "contents": contents,
            "tools": tools_def,
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "AUTO"
                }
            },
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 1024
            }
        }

        # 5. Call Gemini
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=req_headers)
                if resp.status_code != 200:
                    logger.error(f"Gemini API error: {resp.status_code} {resp.text}")
                    if lang == "ru":
                        err_reply = "К сожалению, произошла ошибка связи с искусственным интеллектом. Пожалуйста, попробуйте еще раз."
                    elif lang == "uz_cyrl":
                        err_reply = "Кечирасиз, сунъий интеллект хизмати билан алоқада хатолик юз берди. Илтимос, қайта уриниб кўринг."
                    else:
                        err_reply = "Kechirasiz, sun'iy intellekt xizmati bilan aloqa o'rnatishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
                    return {
                        "ok": False,
                        "reply": err_reply,
                        "error": resp.text
                    }

                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])

                question_cards = []

                # Check if Gemini called a tool
                function_call = next((p.get("functionCall") for p in parts if "functionCall" in p), None)
                if function_call:
                    fn_name = function_call.get("name")
                    fn_args = function_call.get("args", {})
                    logger.info(f"Gemini requested tool: {fn_name} with args: {fn_args}")

                    # Execute tool with user's language
                    tool_fn = TOOL_MAPPING.get(fn_name)
                    if tool_fn:
                        tool_result = tool_fn(fn_args, user_id, lang)
                        
                        # Collect question cards if questions were returned
                        for k in ["questions", "saved_questions", "mistake_questions"]:
                            if k in tool_result:
                                question_cards.extend(tool_result[k])

                        # Sanitize data for LLM so it never sees raw canonical IDs
                        def _clean_for_llm(data):
                            if isinstance(data, dict):
                                return {k: _clean_for_llm(v) for k, v in data.items() if k != "canonical_id"}
                            elif isinstance(data, list):
                                return [_clean_for_llm(item) for item in data]
                            return data

                        gemini_safe_result = _clean_for_llm(tool_result)

                        # Send function response back to Gemini for final user answer
                        fn_response_content = {
                            "role": "function",
                            "parts": [{
                                "functionResponse": {
                                    "name": fn_name,
                                    "response": {"result": gemini_safe_result}
                                }
                            }]
                        }
                        
                        # Update contents with model's functionCall and tool's response
                        updated_contents = list(contents)
                        updated_contents.append(content)
                        updated_contents.append(fn_response_content)

                        second_payload = {
                            "system_instruction": system_instruction,
                            "contents": updated_contents,
                            "generationConfig": {
                                "temperature": 0.35,
                                "maxOutputTokens": 1024
                            }
                        }

                        second_resp = await client.post(url, json=second_payload, headers=req_headers)
                        if second_resp.status_code == 200:
                            second_data = second_resp.json()
                            final_parts = second_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                            final_text = "".join(p.get("text", "") for p in final_parts)
                        else:
                            final_text = "Ma'lumotlar olindi va tahlil qilindi." if lang == "uz_latn" else ("Маълумотлар олинди ва таҳлил қилинди." if lang == "uz_cyrl" else "Данные получены и проанализированы.")
                    else:
                        final_text = "Noma'lum vosita chaqirildi."
                else:
                    final_text = "".join(p.get("text", "") for p in parts)

                # Clean any leaked technical identifiers from final text
                final_text = re.sub(r'\b(?:Canon(?:ical)?\s*(?:yhq)?[:\-]?\s*)?UZ-YHQ-[A-Z0-9]+\b', '', final_text, flags=re.IGNORECASE)
                q_word = "вопрос" if lang == "ru" else ("савол" if lang == "uz_cyrl" else "savol")
                Q_word = "Вопрос" if lang == "ru" else ("Савол" if lang == "uz_cyrl" else "Savol")
                final_text = re.sub(r'\bCanon\s*yhq\b', q_word, final_text, flags=re.IGNORECASE)
                final_text = re.sub(r'\bCanon\b', Q_word, final_text, flags=re.IGNORECASE)

                # Save assistant response
                meta_json = json.dumps({"cards": len(question_cards)}) if question_cards else None
                self.save_message(user_id, session_id, "assistant", final_text, meta_json)

                return {
                    "ok": True,
                    "reply": final_text,
                    "limit_reached": False,
                    "usage": {"current": current_count, "max": max_limit},
                    "cards": question_cards[:3] # return top 3 question cards if any
                }

            except Exception as e:
                logger.exception("AI assistant invocation exception")
                return {
                    "ok": False,
                    "reply": f"AI xizmatida vaqtinchalik xatolik yuz berdi: {str(e)}",
                    "error": str(e)
                }
