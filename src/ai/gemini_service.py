import os
import re
import json
import time
import base64
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx
from src.ai.prompts import SYSTEM_PROMPT_UZ, get_system_prompt
from src.ai.tools import GEMINI_TOOLS_DECLARATIONS, TOOL_MAPPING, normalize_lang
from src.db_adapter import get_db_connection

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite"
]

_KEY_COOLDOWNS: Dict[str, float] = {}

class GeminiService:
    def __init__(self):
        pass

    @property
    def api_keys(self) -> List[str]:
        keys = []
        raw_keys = os.getenv("GEMINI_API_KEYS", "")
        if raw_keys:
            keys.extend([k.strip() for k in raw_keys.split(",") if k.strip()])
        for env_var in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_BACKUP", "GOOGLE_API_KEY"]:
            val = os.getenv(env_var, "").strip()
            if val and val not in keys:
                keys.append(val)
        return keys

    @property
    def api_key(self) -> Optional[str]:
        keys = self.api_keys
        return keys[0] if keys else None

    async def _call_gemini_with_fallback(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[str]]:
        """Calls Gemini API with automatic key rotation and model fallback on 429/503 spikes."""
        last_status = None
        last_text = None
        now = time.time()
        
        # Sort active keys so non-cooldown keys are tried first
        all_keys = self.api_keys
        if not all_keys:
            return None, 500, "No Gemini API keys configured"

        active_keys = sorted(all_keys, key=lambda k: 1 if _KEY_COOLDOWNS.get(k, 0) > now else 0)

        for cur_key in active_keys:
            if _KEY_COOLDOWNS.get(cur_key, 0) > now:
                logger.info(f"Key ...{cur_key[-6:]} in cooldown until {_KEY_COOLDOWNS[cur_key]:.0f}, skipping...")
                continue

            key_exhausted = False
            for model_name in GEMINI_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={cur_key}"
                req_headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": cur_key
                }

                try:
                    resp = await client.post(url, json=payload, headers=req_headers, timeout=22.0)
                    last_status = resp.status_code
                    last_text = resp.text

                    if resp.status_code == 200:
                        return resp.json(), 200, None

                    if resp.status_code == 429:
                        logger.warning(f"Gemini {model_name} returned 429 quota on key ...{cur_key[-6:]}")
                        if last_text and ("quota" in last_text.lower() or "limit" in last_text.lower()):
                            _KEY_COOLDOWNS[cur_key] = now + 600
                            key_exhausted = True
                            break
                        continue

                    if resp.status_code in (503, 500):
                        logger.warning(f"Gemini {model_name} returned {resp.status_code} with key ...{cur_key[-6:]}")
                        continue

                    if resp.status_code == 404:
                        continue
                except Exception as e:
                    logger.warning(f"Gemini request exception on {model_name}: {repr(e)}")
                    last_text = repr(e)
                    continue

            if key_exhausted:
                continue

        return None, last_status, last_text

    @staticmethod
    def _detect_image_mime(data: bytes) -> Optional[str]:
        if not data or len(data) < 12:
            return None
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        return None

    async def _load_image_base64(self, image_url: str) -> Optional[Tuple[str, str]]:
        """Loads question image and returns (base64_str, mime_type).
        Validates image magic bytes to ensure HTML error pages are never sent to Gemini.
        """
        if not image_url:
            return None
        try:
            clean_name = os.path.basename(image_url.split("?")[0].replace("\\", "/"))
            local_path = os.path.join("data", "images", "original", clean_name)

            # 1. Local disk check
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    content = f.read()
                    mime = self._detect_image_mime(content)
                    if mime:
                        return base64.b64encode(content).decode("utf-8"), mime

            # 2. Remote candidates
            candidates = []
            if image_url.startswith("http://") or image_url.startswith("https://"):
                candidates.append(image_url)
            candidates.extend([
                f"https://rully-app.onrender.com/images/{clean_name}",
                f"https://fastly.jsdelivr.net/gh/aralovv/Rully@main/data/images/original/{clean_name}",
                f"https://raw.githubusercontent.com/aralovv/Rully/main/data/images/original/{clean_name}"
            ])
            async with httpx.AsyncClient(timeout=6.0) as client:
                for candidate in candidates:
                    try:
                        r = await client.get(candidate)
                        if r.status_code == 200 and len(r.content) > 12:
                            mime = self._detect_image_mime(r.content)
                            if mime:
                                return base64.b64encode(r.content).decode("utf-8"), mime
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to load image for Gemini vision ({image_url}): {e}")
        return None

    def _get_scene_annotation(self, filename: Optional[str], canonical_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Loads verified visual passport from data/image_scenes.json if available."""
        json_path = os.path.join("data", "image_scenes.json")
        if os.path.exists(json_path):
            try:
                mtime = os.path.getmtime(json_path)
                if not hasattr(self, "_scene_cache") or getattr(self, "_scene_cache_mtime", 0) != mtime:
                    with open(json_path, "r", encoding="utf-8") as f:
                        self._scene_cache = json.load(f)
                        self._scene_cache_mtime = mtime
            except Exception as e:
                logger.warning(f"Error loading image_scenes.json: {e}")
                self._scene_cache = getattr(self, "_scene_cache", {})
        else:
            self._scene_cache = {}

        if filename and filename in self._scene_cache:
            return self._scene_cache[filename]
        if canonical_id:
            for item in self._scene_cache.values():
                if item.get("canonical_id") == canonical_id:
                    return item
        return None

    def _get_db_ground_truth(self, canonical_id: Optional[str], filename: Optional[str], lang: str) -> Optional[Dict[str, Any]]:
        """Retrieves official state exam question, correct answer, legal reference and explanation directly from database."""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                resolved_id = canonical_id
                if not resolved_id and filename:
                    c.execute("""
                    SELECT cq.canonical_id
                    FROM canonical_questions cq
                    JOIN images i ON cq.primary_image_id = i.id
                    WHERE i.filename = ? LIMIT 1
                    """, (filename,))
                    row = c.fetchone()
                    if row:
                        resolved_id = row["canonical_id"] if isinstance(row, dict) else row[0]

                if not resolved_id:
                    return None

                c.execute("""
                SELECT cq.canonical_id, cq.correct_option_key, cq.legal_reference, cq.category_name,
                       ct.question_text, ct.explanation
                FROM canonical_questions cq
                LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                WHERE cq.canonical_id = ?
                """, (lang, resolved_id))
                q_row = c.fetchone()
                if not q_row:
                    return None

                correct_key = q_row["correct_option_key"] if isinstance(q_row, dict) else q_row[1]
                legal_ref = q_row["legal_reference"] if isinstance(q_row, dict) else q_row[2]
                category_name = q_row["category_name"] if isinstance(q_row, dict) else q_row[3]
                q_text = q_row["question_text"] if isinstance(q_row, dict) else q_row[4]
                explanation = q_row["explanation"] if isinstance(q_row, dict) else q_row[5]

                ans_col = f"text_{lang}" if lang in ("uz_latn", "uz_cyrl", "ru") else "text_uz_latn"
                c.execute(f"""
                SELECT option_key, {ans_col}
                FROM canonical_answers
                WHERE canonical_id = ? AND (is_correct = 1 OR option_key = ?)
                LIMIT 1
                """, (resolved_id, correct_key))
                a_row = c.fetchone()
                correct_text = (a_row[ans_col] if isinstance(a_row, dict) else a_row[1]) if a_row else ""

                return {
                    "canonical_id": resolved_id,
                    "category_name": category_name,
                    "question_text": q_text,
                    "correct_key": correct_key,
                    "correct_text": correct_text,
                    "legal_reference": legal_ref,
                    "explanation": explanation
                }
        except Exception as e:
            logger.warning(f"Error fetching DB ground truth: {e}")
            return None

    def _build_ground_truth_context(self, image_url: Optional[str], canonical_id: Optional[str], lang: str) -> Optional[str]:
        """Combines verified scene passport and official DB exam ground truth into an authoritative prompt context."""
        clean_filename = os.path.basename(image_url.split("?")[0].replace("\\", "/")) if image_url else None
        scene = self._get_scene_annotation(clean_filename, canonical_id)
        db_gt = self._get_db_ground_truth(canonical_id, clean_filename, lang)

        if not scene and not db_gt:
            return None

        lines = ["\n[TASDIQLANGAN RASMIY GROUND TRUTH VA VIZUAL SAHNA PASPORTI]:"]

        if db_gt:
            lines.append(f"• Rasmiy to‘g‘ri javob: {db_gt.get('correct_key')}) {db_gt.get('correct_text')}")
            if db_gt.get("legal_reference"):
                lines.append(f"• Rasmiy YHQ qoidasi moddasi: {db_gt.get('legal_reference')}")
            if db_gt.get("explanation"):
                lines.append(f"• Rasmiy imtihon tushuntirishi: {db_gt.get('explanation')}")

        if scene:
            lines.append(f"• Sahna toifasi: {scene.get('sahna_turi') or scene.get('vaziyat_turi', '')}")
            if scene.get("vizual_muhit_va_yo‘l"):
                lines.append(f"• Yo‘l tuzilishi va muhit: {scene.get('vizual_muhit_va_yo‘l')}")
            if scene.get("belgilar_va_chiziqlar"):
                lines.append(f"• Yo‘l belgilari va chiziqlari: {scene.get('belgilar_va_chiziqlar')}")
            if scene.get("tartibga_soluvchi_yoki_svetofor"):
                lines.append(f"• Tartibga soluvchi yoki svetofor: {scene.get('tartibga_soluvchi_yoki_svetofor')}")

            participants = scene.get("ishtirokchilar_va_obyektlar") or scene.get("transport_vositalari") or []
            if participants:
                lines.append("• Ishtirokchilar va transport vositalari:")
                for p in participants:
                    if isinstance(p, dict):
                        name = p.get("obyekt") or p.get("mashina") or "Transport vositasi"
                        pos = p.get("joylashuvi") or ""
                        intent = p.get("harakat_yonalishi_yoki_traektoriya") or p.get("harakat_yonalishi") or ""
                        status = p.get("holati_va_huquqi") or p.get("holati") or ""
                        lines.append(f"  - {name} ({pos}): {intent} -> {status}")

            if scene.get("traektoriyalar_tahlili") and scene.get("traektoriyalar_tahlili") != "Mavjud emas":
                lines.append(f"• Traektoriyalar tahlili (A, B, C): {scene.get('traektoriyalar_tahlili')}")

            otish = scene.get("otish_tartibi_yoki_yechim") or scene.get("otish_ketmaketligi")
            if otish:
                lines.append(f"• O‘tish navbati yoki yechim: {otish}")

        lines.append(
            "QAT'IY KO‘RSATMA: Yuqoridagi faktlar ushbu savol va rasmning davlat imtihoni mezonlariga mos 100% rasmiy tasdiqlangan haqiqatidir. "
            "Foydalanuvchiga tushuntirayotganda ushbu ma'lumotlarga qat'iy tayangan holda professional va aniq javob bering, hech narsani taxmin qilib o'ylab topmang!"
        )

        return "\n".join(lines)

    @staticmethod
    def _build_learner_context(
        student_snapshot: Optional[Dict[str, Any]] = None,
        question_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        blocks = []
        if student_snapshot:
            blocks.append(
                "\n[O‘QUVCHI PROFILI]: "
                f"Yechilgan unikal savollar: {student_snapshot.get('unique_answered', 0)}, "
                f"Imtihonlar: {student_snapshot.get('passed_exams', 0)}/{student_snapshot.get('total_exams', 0)}, "
                f"Faol xatolar banki: {student_snapshot.get('active_mistakes', 0)} ta savol."
            )
        if question_context:
            sel = question_context.get("selected_key")
            is_ok = question_context.get("is_correct")
            if sel:
                blocks.append(
                    f"[TALABA TANLOVI]: O‘quvchi ushbu savolda {sel} variantini tanladi "
                    f"({'To‘g‘ri' if is_ok else 'Noto‘g‘ri javob bergan — aynan nima sababdan bunday bo‘lishini tushuntiring'})."
                )
        return "\n".join(blocks)

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

    def refund_rate_limit(self, user_id: int):
        """Refund 1 request count if external Gemini API call failed or timed out."""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                UPDATE ai_usage_limits
                SET request_count = MAX(0, request_count - 1)
                WHERE user_id = ? AND usage_date = DATE('now')
                """, (user_id,))
                conn.commit()
                logger.info(f"Refunded AI rate limit for user {user_id} due to API failure")
        except Exception as e:
            logger.warning(f"Failed to refund AI rate limit for user {user_id}: {e}")

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

                cleaned: List[Dict[str, Any]] = []
                for r in rows:
                    role = "user" if r["role"] == "user" else "model"
                    txt = (r["content"] or "").strip()
                    if not txt:
                        continue
                    if cleaned and cleaned[-1]["role"] == role:
                        cleaned[-1]["parts"][0]["text"] += f"\n{txt}"
                    else:
                        cleaned.append({"role": role, "parts": [{"text": txt}]})

                while cleaned and cleaned[0]["role"] != "user":
                    cleaned.pop(0)

                return cleaned
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
        language: str = "uz_latn",
        image_url: Optional[str] = None,
        canonical_id: Optional[str] = None,
        question_context: Optional[Dict[str, Any]] = None,
        student_snapshot: Optional[Dict[str, Any]] = None,
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

        # 2. Check API key configuration before consuming rate limit
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
                "usage": {"current": 0, "max": 100},
                "cards": []
            }

        # 3. Rate Limit Check (PRO users fair use limit)
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

        # 3. Save User Message
        user_meta = json.dumps({"image_url": image_url, "canonical_id": canonical_id}) if (image_url or canonical_id) else None
        self.save_message(user_id, session_id, "user", message, user_meta)

        # 4. Build Gemini Payload (with Multimodal Vision if image is present)
        current_parts: List[Dict[str, Any]] = [{"text": message}]
        if image_url:
            img_data = await self._load_image_base64(image_url)
            if img_data:
                b64_str, mime_type = img_data
                current_parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": b64_str
                    }
                })
                logger.info(f"Attached multimodal vision image ({mime_type}) to Gemini request")

        history = self.get_conversation_history(user_id, session_id, limit=8)
        while history and history[-1]["role"] == "user":
            history.pop()
        history.append({"role": "user", "parts": current_parts})
        contents = history
        # Build ground truth, scene passport & live student profile context
        gt_context = self._build_ground_truth_context(image_url, canonical_id, lang)
        learner_ctx = self._build_learner_context(student_snapshot, question_context)
        sys_prompt_text = get_system_prompt(lang)
        if gt_context:
            sys_prompt_text += f"\n\n{gt_context}"
            logger.info(f"Injected official ground truth / scene passport into system instruction for {canonical_id or image_url}")
        if learner_ctx:
            sys_prompt_text += f"\n{learner_ctx}"

        system_instruction = {
            "parts": [{"text": sys_prompt_text}]
        }

        payload = {
            "system_instruction": system_instruction,
            "contents": contents,
            "tools": [{"functionDeclarations": GEMINI_TOOLS_DECLARATIONS}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 1024
            }
        }

        # 5. Call Gemini with automatic fallback, retry & tool-call loop
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                question_cards: List[Dict[str, Any]] = []
                parts: List[Dict[str, Any]] = []

                for _round in range(3):
                    data, status_code, err_text = await self._call_gemini_with_fallback(client, payload)
                    if not data or status_code != 200:
                        logger.error(f"Gemini API error: {status_code} {err_text}")
                        # Refund rate limit since external API call was unsuccessful
                        self.refund_rate_limit(user_id)
                        if lang == "ru":
                            err_reply = "К сожалению, произошла ошибка связи с искусственным интеллектом. Пожалуйста, попробуйте еще раз."
                        elif lang == "uz_cyrl":
                            err_reply = "Кечирасиз, сунъий интеллект хизмати билан алоқада хатолик юз берди. Илтимос, қайта уриниб кўринг."
                        else:
                            err_reply = "Kechirasiz, sun'iy intellekt xizmati bilan aloqa o'rnatishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
                        return {
                            "ok": False,
                            "reply": err_reply,
                            "error": err_text or f"Status {status_code}"
                        }

                    candidate = data.get("candidates", [{}])[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])

                    fn_calls = [p["functionCall"] for p in parts if isinstance(p, dict) and "functionCall" in p]
                    if not fn_calls:
                        break

                    contents.append({"role": "model", "parts": parts})
                    fn_responses = []
                    for fc in fn_calls:
                        fn_name = fc.get("name", "")
                        fn_args = fc.get("args") or {}
                        fn_handler = TOOL_MAPPING.get(fn_name)
                        if fn_handler:
                            try:
                                tool_result = fn_handler(fn_args, user_id, lang)
                            except Exception as tool_err:
                                logger.warning(f"Tool execution failed ({fn_name}): {tool_err}")
                                tool_result = {"error": str(tool_err)}
                        else:
                            tool_result = {"error": f"Unknown tool: {fn_name}"}

                        if isinstance(tool_result, dict):
                            for key in ("questions", "mistake_questions", "bookmarks"):
                                if isinstance(tool_result.get(key), list):
                                    for item in tool_result[key]:
                                        if len(question_cards) < 3 and isinstance(item, dict):
                                            question_cards.append({
                                                "canonical_id": item.get("canonical_id"),
                                                "category_name": item.get("category_name"),
                                                "question": item.get("question"),
                                                "correct_option_key": item.get("correct_option_key"),
                                            })

                        fn_responses.append({
                            "functionResponse": {
                                "name": fn_name,
                                "response": tool_result if isinstance(tool_result, dict) else {"result": tool_result},
                            }
                        })
                    contents.append({"role": "user", "parts": fn_responses})
                    payload["contents"] = contents

                final_text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))

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
                    "cards": question_cards[:3]
                }

            except Exception as e:
                logger.exception("AI assistant invocation exception")
                self.refund_rate_limit(user_id)
                return {
                    "ok": False,
                    "reply": f"AI xizmatida vaqtinchalik xatolik yuz berdi: {str(e)}",
                    "error": str(e)
                }
