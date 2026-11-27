import os
import re
import json
import time
import base64
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import httpx
from src.ai.prompts import SYSTEM_PROMPT_UZ, get_system_prompt
from src.ai.tools import (
    GEMINI_TOOLS_DECLARATIONS,
    TOOL_MAPPING,
    normalize_lang,
    get_provenance_select_sql,
    format_legal_provenance_payload,
)
from src.analytics.tracker import log_user_event
from src.db_adapter import get_db_connection

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite"
]

_KEY_COOLDOWNS: Dict[str, float] = {}
_TASHKENT_TZ = timezone(timedelta(hours=5))
_ALLOWED_IMAGE_HOSTS = frozenset({
    "fastly.jsdelivr.net",
    "cdn.jsdelivr.net",
    "raw.githubusercontent.com",
    "rully-app.onrender.com",
    "rully-three.vercel.app",
})
_SAFE_IMAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}\.(?:webp|png|jpe?g)$", re.IGNORECASE)
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

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
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
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

    @staticmethod
    def _tashkent_today_str() -> str:
        return datetime.now(_TASHKENT_TZ).date().isoformat()

    @staticmethod
    def _resolve_trusted_image_filename(image_url: Optional[str], canonical_id: Optional[str] = None) -> Optional[str]:
        """Resolves only an allowlisted or canonical DB image filename (prevents arbitrary SSRF)."""
        if canonical_id:
            try:
                with get_db_connection() as conn:
                    row = conn.execute(
                        """
                        SELECT i.filename
                        FROM canonical_questions cq
                        JOIN images i ON cq.primary_image_id = i.id
                        WHERE cq.canonical_id = ?
                        LIMIT 1
                        """,
                        (str(canonical_id).strip(),),
                    ).fetchone()
                    if row:
                        db_name = os.path.basename(str(row["filename"] if hasattr(row, "keys") else row[0]).replace("\\", "/"))
                        if _SAFE_IMAGE_NAME_RE.fullmatch(db_name):
                            return db_name
            except Exception:
                pass

        if not image_url:
            return None

        raw = str(image_url).strip()
        parsed = urlparse(raw)
        if parsed.scheme:
            if parsed.scheme.lower() != "https":
                return None
            host = (parsed.hostname or "").lower()
            if host not in _ALLOWED_IMAGE_HOSTS:
                return None
        elif not raw.startswith("/images/") and "/" in raw.lstrip("/"):
            return None

        clean_name = os.path.basename(parsed.path.replace("\\", "/"))
        if not _SAFE_IMAGE_NAME_RE.fullmatch(clean_name):
            return None
        return clean_name

    async def _load_image_base64(self, image_url: Optional[str], canonical_id: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Loads question image strictly from local disk or pinned CDN hosts (no arbitrary remote SSRF)."""
        clean_name = self._resolve_trusted_image_filename(image_url, canonical_id=canonical_id)
        if not clean_name:
            return None
        try:
            local_path = os.path.join("data", "images", "original", clean_name)

            # 1. Local disk check
            if os.path.exists(local_path) and os.path.getsize(local_path) <= _MAX_IMAGE_BYTES:
                with open(local_path, "rb") as f:
                    content = f.read(_MAX_IMAGE_BYTES + 1)
                    if len(content) <= _MAX_IMAGE_BYTES:
                        mime = self._detect_image_mime(content)
                        if mime:
                            return base64.b64encode(content).decode("utf-8"), mime

            # 2. Pinned CDN-first remote candidates (no arbitrary client URL fetching & no redirects)
            candidates = [
                f"https://fastly.jsdelivr.net/gh/aralovv/Rully@main/data/images/original/{clean_name}",
                f"https://raw.githubusercontent.com/aralovv/Rully/main/data/images/original/{clean_name}",
                f"https://rully-app.onrender.com/images/{clean_name}",
            ]
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=False) as client:
                for candidate in candidates:
                    try:
                        r = await client.get(candidate)
                        if r.status_code != 200:
                            continue
                        cl = r.headers.get("Content-Length")
                        if cl and int(cl) > _MAX_IMAGE_BYTES:
                            continue
                        if 12 < len(r.content) <= _MAX_IMAGE_BYTES:
                            mime = self._detect_image_mime(r.content)
                            if mime:
                                return base64.b64encode(r.content).decode("utf-8"), mime
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to load image for Gemini vision ({clean_name}): {e}")
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

                prov_sql = get_provenance_select_sql(conn, "cq")
                c.execute(f"""
                SELECT cq.canonical_id, cq.correct_option_key, cq.legal_reference, cq.category_name,
                       ct.question_text, ct.explanation,
                       {prov_sql}
                FROM canonical_questions cq
                LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
                WHERE cq.canonical_id = ?
                """, (lang, resolved_id))
                q_row = c.fetchone()
                if not q_row:
                    return None

                if isinstance(q_row, dict) or hasattr(q_row, "keys"):
                    q_dict = dict(q_row)
                else:
                    q_dict = {
                        "canonical_id": q_row[0],
                        "correct_option_key": q_row[1],
                        "legal_reference": q_row[2],
                        "category_name": q_row[3],
                        "question_text": q_row[4],
                        "explanation": q_row[5],
                        "legal_verification_status": q_row[6] if len(q_row) > 6 else None,
                        "legal_doc_title": q_row[7] if len(q_row) > 7 else None,
                        "legal_chapter": q_row[8] if len(q_row) > 8 else None,
                        "legal_clause": q_row[9] if len(q_row) > 9 else None,
                        "legal_doc_url": q_row[10] if len(q_row) > 10 else None,
                    }

                correct_key = q_dict["correct_option_key"]
                category_name = q_dict["category_name"]
                q_text = q_dict["question_text"]
                explanation = q_dict["explanation"]
                prov = format_legal_provenance_payload(q_dict)

                ans_col = f"text_{lang}" if lang in ("uz_latn", "uz_cyrl", "ru") else "text_uz_latn"
                c.execute(f"""
                SELECT option_key, {ans_col}
                FROM canonical_answers
                WHERE canonical_id = ? AND (is_correct = 1 OR option_key = ?)
                LIMIT 1
                """, (resolved_id, correct_key))
                a_row = c.fetchone()
                correct_text = (a_row[ans_col] if (isinstance(a_row, dict) or hasattr(a_row, "keys")) else a_row[1]) if a_row else ""

                return {
                    "canonical_id": resolved_id,
                    "category_name": category_name,
                    "question_text": q_text,
                    "correct_key": correct_key,
                    "correct_text": correct_text,
                    "explanation": explanation,
                    **prov,
                }
        except Exception as e:
            logger.warning(f"Error fetching DB ground truth: {e}")
            return None

    def _resolve_ground_truth_bundle(
        self,
        image_url: Optional[str],
        canonical_id: Optional[str],
        lang: str,
        question_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Builds prompt ground truth context and returns resolved DB metadata for post-guardrails."""
        clean_filename = self._resolve_trusted_image_filename(image_url, canonical_id=canonical_id)
        scene = self._get_scene_annotation(clean_filename, canonical_id)
        db_gt = self._get_db_ground_truth(canonical_id, clean_filename, lang)

        # Provenance must come solely from authoritative DB rows — never accept client-supplied provenance flags.
        if not scene and not db_gt:
            return None, None

        lines = ["\n[TASDIQLANGAN RASMIY GROUND TRUTH VA VIZUAL SAHNA PASPORTI]:"]

        if db_gt:
            if db_gt.get("correct_key"):
                lines.append(f"• Rasmiy to‘g‘ri javob: {db_gt.get('correct_key')}) {db_gt.get('correct_text') or ''}".strip())
            v_status = db_gt.get("legal_verification_status") or "UNRESOLVED_LEGAL_REVIEW"
            if v_status == "VERIFIED_PRIMARY_LAW":
                doc = db_gt.get("legal_doc_title") or "VMQ 172"
                parts = [p for p in (doc, db_gt.get("legal_chapter"), db_gt.get("legal_clause"), db_gt.get("legal_reference")) if p]
                lines.append(f"• Tasdiqlangan YHQ manbasi ({v_status}): {' | '.join(parts)}")
            elif v_status == "VERIFIED_FIRST_AID_OR_TECH":
                lines.append(
                    "• Huquqiy maqom (VERIFIED_FIRST_AID_OR_TECH): Bu savol birinchi tibbiy yordam yoki texnik xavfsizlik mezoniga oid. "
                    "Bunda VMQ 172 bob/band raqamini to‘qib chiqarmang."
                )
            else:
                lines.append(
                    "• DIQQAT HUQUQIY GUARDRAIL (UNRESOLVED_LEGAL_REVIEW): Ushbu savolning rasmiy VMQ 172 bandi/moddasi hozirda huquqiy tekshiruvda! "
                    "Javobda HECH QANDAY taxminiy VMQ 172 band yoki modda raqamini o‘ylab topmang; faqat qoida mantiqi va tasdiqlangan javobni tushuntiring."
                )
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

        return "\n".join(lines), db_gt

    def _build_ground_truth_context(self, image_url: Optional[str], canonical_id: Optional[str], lang: str) -> Optional[str]:
        """Combines verified scene passport and official DB exam ground truth into an authoritative prompt context."""
        ctx, _ = self._resolve_ground_truth_bundle(image_url, canonical_id, lang)
        return ctx

    @staticmethod
    def _apply_legal_citation_guardrail(
        reply_text: str,
        db_gt: Optional[Dict[str, Any]],
        lang: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Prevents fabricated VMQ 172 citations from reaching students on unverified legal items."""
        if not db_gt:
            return reply_text, {
                "has_db_ground_truth": False,
                "legal_verification_status": None,
                "citation_flagged": False,
            }

        status = db_gt.get("legal_verification_status") or "UNRESOLVED_LEGAL_REVIEW"
        meta: Dict[str, Any] = {
            "has_db_ground_truth": True,
            "legal_verification_status": status,
            "legal_doc_title": db_gt.get("legal_doc_title"),
            "legal_chapter": db_gt.get("legal_chapter"),
            "legal_clause": db_gt.get("legal_clause"),
            "citation_flagged": False,
        }

        if status == "UNRESOLVED_LEGAL_REVIEW":
            unverified_pattern = re.compile(
                r"(?:\b(?:VMQ|PKM|ВМҚ|ПКМ)\s*(?:№|-)?\s*172\b|\b\d{1,3}(?:\.\d{1,3})?[-\s]*(?:band|bandi|modda|moddasi|банд|банди|модда|пункт)\b|\b(?:пункт|п\.?)\s*\d{1,3}(?:\.\d{1,3})?\b)",
                flags=re.IGNORECASE,
            )
            if unverified_pattern.search(reply_text or ""):
                meta["citation_flagged"] = True
                if lang == "ru":
                    note = (
                        "\n\n⚠️ Примечание редакции: точный номер пункта ПКМ 172 по данному вопросу "
                        "сейчас проходит юридическую проверку; опирайтесь на логику правила и официальный ответ."
                    )
                elif lang == "uz_cyrl":
                    note = (
                        "\n\n⚠️ Таҳририят эслатмаси: ушбу савол бўйича аниқ ВМҚ 172 банд рақами ҳозирда ҳуқуқий "
                        "текширувда; тасдиқланган жавоб ва қоида моҳиятига таянинг."
                    )
                else:
                    note = (
                        "\n\n⚠️ Tahririyat eslatmasi: ushbu savol bo‘yicha aniq VMQ 172 band raqami hozirda huquqiy "
                        "tekshiruvda; tasdiqlangan javob va qoida mohiyatiga tayaning."
                    )
                if "tekshiruvda" not in reply_text.lower() and "проходит юридическую проверку" not in reply_text.lower():
                    reply_text = f"{reply_text.rstrip()}{note}"

        return reply_text, meta

    @staticmethod
    def _build_learner_context(
        student_snapshot: Optional[Dict[str, Any]] = None,
        question_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        blocks = []
        if student_snapshot:
            srs_part = ""
            if "srs_due_now" in student_snapshot or "srs_tracked_total" in student_snapshot:
                srs_part = (
                    f" Aqlli Takrorlash (SM-2): muddati kelgan {student_snapshot.get('srs_due_now', 0)} ta, "
                    f"o‘zlashtirilgan {student_snapshot.get('srs_mastered_count', 0)}/{student_snapshot.get('srs_tracked_total', 0)} ta savol."
                )
            blocks.append(
                "\n[O‘QUVCHI PROFILI]: "
                f"Yechilgan unikal savollar: {student_snapshot.get('unique_answered', 0)}, "
                f"Imtihonlar: {student_snapshot.get('passed_exams', 0)}/{student_snapshot.get('total_exams', 0)}, "
                f"Faol xatolar banki: {student_snapshot.get('active_mistakes', 0)} ta savol.{srs_part}"
            )
        if question_context and isinstance(question_context, dict):
            sel = str(question_context.get("selected_key") or "").strip().upper()
            is_ok = bool(question_context.get("is_correct"))
            if sel in {"A", "B", "C", "D", "E"}:
                blocks.append(
                    f"[TALABA TANLOVI]: O‘quvchi ushbu savolda {sel} variantini tanladi "
                    f"({'To‘g‘ri' if is_ok else 'Noto‘g‘ri javob bergan — aynan nima sababdan bunday bo‘lishini tushuntiring'})."
                )
        return "\n".join(blocks)

    def check_and_increment_rate_limit(self, user_id: int, is_pro: bool) -> tuple[bool, int, int]:
        """
        Atomically enforces daily AI Ustoz quota (Tashkent UTC+5 calendar day):
        - PRO users: up to 100 requests per day.
        - Free users: 3 complimentary daily teaser analyses to experience AI Ustoz.
        Returns: (allowed: bool, current_usage: int, max_limit: int)
        """
        max_limit = 100 if is_pro else 3
        today = self._tashkent_today_str()
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT OR IGNORE INTO ai_usage_limits (user_id, usage_date, request_count)
                VALUES (?, ?, 0)
                """,
                (user_id, today),
            )
            c.execute(
                """
                UPDATE ai_usage_limits
                SET request_count = request_count + 1
                WHERE user_id = ? AND usage_date = ? AND request_count < ?
                """,
                (user_id, today, max_limit),
            )
            allowed = (c.rowcount or 0) > 0
            c.execute(
                """
                SELECT request_count FROM ai_usage_limits
                WHERE user_id = ? AND usage_date = ?
                """,
                (user_id, today),
            )
            row = c.fetchone()
            conn.commit()
            current = int(row["request_count"] if hasattr(row, "keys") else row[0]) if row else 0
            return allowed, current, max_limit

    def refund_rate_limit(self, user_id: int):
        """Refund 1 request count if external Gemini API call failed or timed out."""
        today = self._tashkent_today_str()
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                UPDATE ai_usage_limits
                SET request_count = MAX(0, request_count - 1)
                WHERE user_id = ? AND usage_date = ?
                """, (user_id, today))
                conn.commit()
                logger.info(f"Refunded AI rate limit for user {user_id} due to API failure")
        except Exception as e:
            logger.warning(f"Failed to refund AI rate limit for user {user_id}: {e}")

    def get_conversation_history(
        self,
        user_id: int,
        session_id: str,
        limit: int = 10,
        include_meta: bool = False,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                SELECT role, content, meta_json FROM ai_conversations
                WHERE user_id = ? AND session_id = ?
                ORDER BY id DESC LIMIT ?
                """, (user_id, session_id, limit))
                rows = c.fetchall()
                rows.reverse()  # chronological

                if include_meta:
                    raw_out: List[Dict[str, Any]] = []
                    for r in rows:
                        txt = (r["content"] or "").strip()
                        if not txt:
                            continue
                        meta = {}
                        raw_meta = r["meta_json"] if hasattr(r, "keys") and "meta_json" in r.keys() else (r[2] if len(r) > 2 else None)
                        if raw_meta:
                            try:
                                parsed = json.loads(raw_meta)
                                if isinstance(parsed, dict):
                                    meta = parsed
                            except Exception:
                                pass
                        raw_out.append({
                            "role": "user" if r["role"] == "user" else "assistant",
                            "text": txt,
                            "cards": meta.get("cards") if isinstance(meta.get("cards"), list) else [],
                            "grounding": meta.get("grounding"),
                        })
                    return raw_out

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

    def save_message(self, user_id: int, session_id: str, role: str, content: str, meta_json: Optional[str] = None) -> Optional[int]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                INSERT INTO ai_conversations (user_id, session_id, role, content, meta_json)
                VALUES (?, ?, ?, ?, ?)
                """, (user_id, session_id, role, content, meta_json))
                row_id = c.lastrowid
                conn.commit()
                return int(row_id) if row_id else None
        except Exception as e:
            logger.warning(f"Failed to persist AI conversation message: {e}")
            return None

    def _delete_message_by_id(self, msg_id: Optional[int]) -> None:
        if not msg_id:
            return
        try:
            with get_db_connection() as conn:
                conn.execute("DELETE FROM ai_conversations WHERE id = ?", (msg_id,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to rollback orphan AI message #{msg_id}: {e}")

    def _post_process_reply(
        self,
        raw_text: str,
        db_gt_meta: Optional[Dict[str, Any]],
        lang: str,
    ) -> Tuple[str, Dict[str, Any]]:
        final_text = re.sub(r'\b(?:Canon(?:ical)?\s*(?:yhq)?[:\-]?\s*)?UZ-YHQ-[A-Z0-9]+\b', '', raw_text or '', flags=re.IGNORECASE)
        q_word = "вопрос" if lang == "ru" else ("савол" if lang == "uz_cyrl" else "savol")
        Q_word = "Вопрос" if lang == "ru" else ("Савол" if lang == "uz_cyrl" else "Savol")
        final_text = re.sub(r'\bCanon\s*yhq\b', q_word, final_text, flags=re.IGNORECASE)
        final_text = re.sub(r'\bCanon\b', Q_word, final_text, flags=re.IGNORECASE)
        return self._apply_legal_citation_guardrail(final_text, db_gt_meta, lang)

    async def _prepare_turn_context(
        self,
        user_id: int,
        session_id: str,
        message: str,
        is_pro: bool,
        language: str,
        image_url: Optional[str],
        canonical_id: Optional[str],
        question_context: Optional[Dict[str, Any]],
        student_snapshot: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        lang = normalize_lang(language)

        if not self.api_key:
            reply = (
                "⚠️ **AI Инструктор настраивается.**\n\nСервис скоро заработает в полном объеме."
                if lang == "ru"
                else (
                    "⚠️ **AI Устоз хизмати созланмоқда.**\n\nТез орада тўлиқ ишга тушади."
                    if lang == "uz_cyrl"
                    else "⚠️ **AI Ustoz xizmati sozlanmoqda.**\n\nTez orada to'liq ishga tushadi."
                )
            )
            return {
                "ok": True,
                "reply": reply,
                "limit_reached": False,
                "usage": {"current": 0, "max": 100 if is_pro else 3},
                "cards": [],
            }, None

        allowed, current_count, max_limit = await asyncio.to_thread(self.check_and_increment_rate_limit, user_id, is_pro)
        if not allowed:
            if not is_pro:
                limit_msg = (
                    f"🔒 **Kunlik {max_limit} ta bepul AI tahlil tugadi!**\n\n⚡ Cheksiz savol-javob, 7 kunlik o‘qish rejasi va rasm tahlili uchun **RULLY PRO** obunasini yoqing."
                    if lang == "uz_latn"
                    else (
                        f"🔒 **Кунлик {max_limit} та бепул AI таҳлил тугади!**\n\n⚡ Чексиз савол-жавоб ва 7 кунлик режа учун **RULLY PRO** обунасини ёқинг."
                        if lang == "uz_cyrl"
                        else f"🔒 **Использованы {max_limit} бесплатных AI-разбора за день!**\n\n⚡ Подключите **RULLY PRO** для безлимитного ИИ-наставника и 7-дневного плана подготовки."
                    )
                )
            else:
                limit_msg = (
                    f"Ваш дневной лимит запросов к AI ({max_limit}) исчерпан. Пожалуйста, продолжите завтра."
                    if lang == "ru"
                    else (
                        f"Кунлик AI сўровлар лимитингиз ({max_limit} та) тугади. Илтимос, эртага давом этинг."
                        if lang == "uz_cyrl"
                        else f"Kunlik AI so‘rovlar limitingiz ({max_limit} ta) tugadi. Iltimos, ertaga davom eting."
                    )
                )
            return {
                "ok": False,
                "requires_pro": not is_pro,
                "reply": limit_msg,
                "limit_reached": True,
                "usage": {"current": current_count, "max": max_limit},
                "cards": [],
            }, None

        user_meta = json.dumps({"image_url": image_url, "canonical_id": canonical_id}) if (image_url or canonical_id) else None
        user_msg_id = await asyncio.to_thread(self.save_message, user_id, session_id, "user", message, user_meta)

        current_parts: List[Dict[str, Any]] = [{"text": message}]
        if image_url or canonical_id:
            img_data = await self._load_image_base64(image_url, canonical_id=canonical_id)
            if img_data:
                b64_str, mime_type = img_data
                current_parts.append({"inline_data": {"mime_type": mime_type, "data": b64_str}})

        history = await asyncio.to_thread(self.get_conversation_history, user_id, session_id, 8, False)
        while history and history[-1]["role"] == "user":
            history.pop()
        history.append({"role": "user", "parts": current_parts})

        gt_context, db_gt_meta = await asyncio.to_thread(
            self._resolve_ground_truth_bundle, image_url, canonical_id, lang, question_context
        )
        learner_ctx = self._build_learner_context(student_snapshot, question_context)
        sys_prompt_text = get_system_prompt(lang)
        if gt_context:
            sys_prompt_text += f"\n\n{gt_context}"
        if learner_ctx:
            sys_prompt_text += f"\n{learner_ctx}"

        payload = {
            "system_instruction": {"parts": [{"text": sys_prompt_text}]},
            "contents": history,
            "tools": [{"functionDeclarations": GEMINI_TOOLS_DECLARATIONS}],
            "generationConfig": {"temperature": 0.35, "maxOutputTokens": 1024},
        }
        return None, {
            "lang": lang,
            "current_count": current_count,
            "max_limit": max_limit,
            "user_msg_id": user_msg_id,
            "contents": history,
            "db_gt_meta": db_gt_meta,
            "payload": payload,
        }

    @staticmethod
    def _collect_cards_from_tool_result(tool_result: Dict[str, Any], question_cards: List[Dict[str, Any]]) -> None:
        seen = {c.get("canonical_id") for c in question_cards if c.get("canonical_id")}
        for key in ("questions", "mistake_questions", "bookmarks", "saved_questions", "srs_items", "top_mistake_questions"):
            if isinstance(tool_result.get(key), list):
                for item in tool_result[key]:
                    if len(question_cards) >= 3:
                        return
                    if isinstance(item, dict) and item.get("canonical_id") not in seen:
                        seen.add(item.get("canonical_id"))
                        question_cards.append({
                            "canonical_id": item.get("canonical_id"),
                            "category_name": item.get("category_name"),
                            "question": item.get("question"),
                            "correct_option_key": item.get("correct_option_key"),
                        })

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
        early_resp, ctx = await self._prepare_turn_context(
            user_id, session_id, message, is_pro, language,
            image_url, canonical_id, question_context, student_snapshot,
        )
        if early_resp:
            return early_resp

        lang = ctx["lang"]
        current_count = ctx["current_count"]
        max_limit = ctx["max_limit"]
        user_msg_id = ctx["user_msg_id"]
        contents = ctx["contents"]
        db_gt_meta = ctx["db_gt_meta"]
        payload = ctx["payload"]

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                question_cards: List[Dict[str, Any]] = []
                parts: List[Dict[str, Any]] = []

                for _round in range(3):
                    data, status_code, err_text = await self._call_gemini_with_fallback(client, payload)
                    if not data or status_code != 200:
                        logger.error(f"Gemini API error: {status_code} {err_text}")
                        await asyncio.to_thread(self.refund_rate_limit, user_id)
                        await asyncio.to_thread(self._delete_message_by_id, user_msg_id)
                        err_reply = (
                            "К сожалению, произошла ошибка связи с искусственным интеллектом. Пожалуйста, попробуйте еще раз."
                            if lang == "ru"
                            else (
                                "Кечирасиз, сунъий интеллект хизмати билан алоқада хатолик юз берди. Илтимос, қайта уриниб кўринг."
                                if lang == "uz_cyrl"
                                else "Kechirasiz, sun'iy intellekt xizmati bilan aloqa o'rnatishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
                            )
                        )
                        return {"ok": False, "reply": err_reply, "error": err_text or f"Status {status_code}"}

                    candidate = data.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
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
                                tool_result = await asyncio.to_thread(fn_handler, fn_args, user_id, lang)
                            except Exception as tool_err:
                                logger.warning(f"Tool execution failed ({fn_name}): {tool_err}")
                                tool_result = {"error": str(tool_err)}
                        else:
                            tool_result = {"error": f"Unknown tool: {fn_name}"}

                        if isinstance(tool_result, dict):
                            self._collect_cards_from_tool_result(tool_result, question_cards)

                        fn_responses.append({
                            "functionResponse": {
                                "name": fn_name,
                                "response": tool_result if isinstance(tool_result, dict) else {"result": tool_result},
                            }
                        })
                    contents.append({"role": "user", "parts": fn_responses})
                    payload["contents"] = contents

                raw_text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                final_text, grounding_meta = self._post_process_reply(raw_text, db_gt_meta, lang)

                persisted_cards = question_cards[:3]
                meta_json = json.dumps({"cards": persisted_cards, "grounding": grounding_meta})
                await asyncio.to_thread(self.save_message, user_id, session_id, "assistant", final_text, meta_json)
                try:
                    await asyncio.to_thread(log_user_event, user_id, "AI_CHAT_USED", {"canonical_id": canonical_id, "is_pro": is_pro})
                except Exception:
                    pass

                return {
                    "ok": True,
                    "reply": final_text,
                    "limit_reached": False,
                    "usage": {"current": current_count, "max": max_limit},
                    "cards": persisted_cards,
                    "grounding": grounding_meta,
                }
            except Exception:
                logger.exception("AI assistant invocation exception")
                await asyncio.to_thread(self.refund_rate_limit, user_id)
                await asyncio.to_thread(self._delete_message_by_id, user_msg_id)
                return {
                    "ok": False,
                    "reply": "AI xizmatida vaqtinchalik xatolik yuz berdi. Iltimos, birozdan so‘ng qayta urinib ko‘ring.",
                    "error": "temporary_ai_error",
                }

    async def stream_chat(
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
    ) -> AsyncIterator[str]:
        """Yields Server-Sent Events (SSE) JSON frames for real-time AI Ustoz token streaming."""
        status_label = "Savol tahlil qilinmoqda..." if language != "ru" else "Анализируем вопрос..."
        yield f"data: {json.dumps({'type': 'status', 'text': status_label}, ensure_ascii=False)}\n\n"
        result = await self.chat(
            user_id=user_id,
            session_id=session_id,
            message=message,
            is_pro=is_pro,
            language=language,
            image_url=image_url,
            canonical_id=canonical_id,
            question_context=question_context,
            student_snapshot=student_snapshot,
        )
        if not result.get("ok") and not result.get("reply"):
            yield f"data: {json.dumps({'type': 'error', **result}, ensure_ascii=False)}\n\n"
            return

        reply = result.get("reply") or ""
        chunk_size = 24
        for idx in range(0, len(reply), chunk_size):
            piece = reply[idx:idx + chunk_size]
            yield f"data: {json.dumps({'type': 'delta', 'text': piece}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.012)

        yield f"data: {json.dumps({'type': 'done', **result}, ensure_ascii=False)}\n\n"
