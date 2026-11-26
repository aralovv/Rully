import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from src.db_adapter import get_db_connection
from src.bot.category_localization import localize_category

_PROVENANCE_COLUMNS = (
    "legal_verification_status",
    "legal_doc_title",
    "legal_chapter",
    "legal_clause",
    "legal_doc_url",
)

def normalize_lang(language: Optional[str]) -> str:
    lang = (language or "uz_latn").lower().strip()
    if lang in ("ru", "russian"):
        return "ru"
    if lang in ("uz_cyrl", "cyrl", "kirill"):
        return "uz_cyrl"
    return "uz_latn"

def get_provenance_select_sql(conn: Any, alias: str = "cq") -> str:
    """Returns safe SELECT column expressions for legal provenance across v1/v2 schemas."""
    try:
        c = conn.cursor()
        c.execute("PRAGMA table_info(canonical_questions)")
        existing = {row[1] if isinstance(row, tuple) else row["name"] for row in c.fetchall()}
    except Exception:
        existing = set()
    exprs = []
    for col in _PROVENANCE_COLUMNS:
        if col in existing:
            exprs.append(f"{alias}.{col}")
        else:
            exprs.append(f"NULL AS {col}")
    return ", ".join(exprs)

def format_legal_provenance_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """Formats legal verification metadata and prevents unverified VMQ citations."""
    status = row.get("legal_verification_status") or (
        "VERIFIED_PRIMARY_LAW" if row.get("legal_reference") else "UNRESOLVED_LEGAL_REVIEW"
    )
    legal_ref = row.get("legal_reference")
    doc_title = row.get("legal_doc_title")
    chapter = row.get("legal_chapter")
    clause = row.get("legal_clause")
    doc_url = row.get("legal_doc_url")

    if status == "UNRESOLVED_LEGAL_REVIEW":
        note = "UNRESOLVED_LEGAL_REVIEW: Rasmiy VMQ 172 bandi tekshiruvda — taxminiy modda raqamini yozmang."
        safe_ref = None
    elif status == "VERIFIED_FIRST_AID_OR_TECH":
        note = "VERIFIED_FIRST_AID_OR_TECH: Birinchi tibbiy yordam yoki texnik xavfsizlik qoidasi (VMQ 172 moddasi emas)."
        safe_ref = legal_ref
    else:
        note = "VERIFIED_PRIMARY_LAW"
        safe_ref = legal_ref

    return {
        "legal_reference": safe_ref,
        "legal_verification_status": status,
        "legal_doc_title": doc_title,
        "legal_chapter": chapter,
        "legal_clause": clause,
        "legal_doc_url": doc_url,
        "legal_guardrail_note": note,
    }

def tool_search_questions(
    query: str,
    category_id: Optional[int] = None,
    limit: int = 3,
    language: str = "uz_latn"
) -> Dict[str, Any]:
    """1327 ta savol ichidan qidirish (savol matni, izohi yoki qonuniy havolasi bo‘yicha)."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        lang = normalize_lang(language)
        col_text = f"text_{lang}"
        q_pattern = f"%{query}%"
        prov_sql = get_provenance_select_sql(conn, "cq")
        
        cat_sql = ""
        params = [lang, q_pattern, q_pattern, q_pattern]
        if category_id is not None:
            cat_sql = " AND cq.category_id = ? "
            params.append(category_id)
            
        params.append(min(limit, 5))
        
        sql = f"""
        SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.correct_option_key, cq.legal_reference,
               {prov_sql},
               ct.question_text, ct.explanation
        FROM canonical_questions cq
        JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = ?
        WHERE (ct.question_text LIKE ? OR ct.explanation LIKE ? OR cq.legal_reference LIKE ?)
        {cat_sql}
        LIMIT ?
        """
        c.execute(sql, tuple(params))
        rows = c.fetchall()
        
        # If no results in selected language, fall back to searching in uz_latn
        if not rows and lang != "uz_latn":
            fallback_params = ["uz_latn", q_pattern, q_pattern, q_pattern]
            if category_id is not None:
                fallback_params.append(category_id)
            fallback_params.append(min(limit, 5))
            c.execute(sql, tuple(fallback_params))
            rows = c.fetchall()
        
        answers_by_cid = {}
        if rows:
            cids = [r["canonical_id"] for r in rows]
            placeholders = ",".join("?" * len(cids))
            c.execute(f"""
                SELECT canonical_id, option_key, {col_text} AS opt_text
                FROM canonical_answers
                WHERE canonical_id IN ({placeholders})
                ORDER BY canonical_id, sort_order
            """, tuple(cids))
            for a in c.fetchall():
                answers_by_cid.setdefault(a["canonical_id"], []).append({"key": a["option_key"], "text": a["opt_text"]})

        results = []
        for idx, r in enumerate(rows):
            rd = dict(r)
            cid = rd["canonical_id"]
            prov = format_legal_provenance_payload(rd)
            results.append({
                "canonical_id": cid,
                "question_number": idx + 1,
                "category_name": localize_category(rd["category_name"], lang),
                "question": rd["question_text"],
                "explanation": rd["explanation"],
                "correct_option_key": rd["correct_option_key"],
                "options": answers_by_cid.get(cid, []),
                **prov,
            })
            
        return {
            "count": len(results),
            "questions": results
        }

def tool_get_user_bookmarks(user_id: int, limit: int = 5, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining saqlangan (bookmark) savollarini olish."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        lang = normalize_lang(language)
        col_text = f"text_{lang}"
        
        c.execute("""
        SELECT ub.canonical_id, cq.category_name, cq.correct_option_key, cq.legal_reference,
               ct.question_text, ct.explanation
        FROM user_bookmarks ub
        JOIN canonical_questions cq ON ub.canonical_id = cq.canonical_id
        JOIN canonical_translations ct ON ub.canonical_id = ct.canonical_id AND ct.language = ?
        WHERE ub.user_id = ?
        ORDER BY ub.created_at DESC
        LIMIT ?
        """, (lang, user_id, min(limit, 10)))
        
        rows = c.fetchall()
        answers_by_cid = {}
        if rows:
            cids = [r["canonical_id"] for r in rows]
            placeholders = ",".join("?" * len(cids))
            c.execute(f"""
                SELECT canonical_id, option_key, {col_text} AS opt_text
                FROM canonical_answers
                WHERE canonical_id IN ({placeholders})
                ORDER BY canonical_id, sort_order
            """, tuple(cids))
            for a in c.fetchall():
                answers_by_cid.setdefault(a["canonical_id"], []).append({"key": a["option_key"], "text": a["opt_text"]})

        results = []
        for idx, r in enumerate(rows):
            cid = r["canonical_id"]
            results.append({
                "canonical_id": cid,
                "question_number": idx + 1,
                "category_name": localize_category(r["category_name"], lang),
                "question": r["question_text"],
                "legal_reference": r["legal_reference"],
                "explanation": r["explanation"],
                "correct_option_key": r["correct_option_key"],
                "options": answers_by_cid.get(cid, [])
            })
            
        return {
            "count": len(results),
            "saved_questions": results
        }

def tool_get_user_mistakes(user_id: int, limit: int = 5, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining testlarda adashgan (xato qilgan) savollarini olish."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        lang = normalize_lang(language)
        col_text = f"text_{lang}"
        prov_sql = get_provenance_select_sql(conn, "cq")
        
        c.execute(f"""
        SELECT um.canonical_id, um.mistake_count, cq.category_name, cq.correct_option_key, cq.legal_reference,
               {prov_sql},
               ct.question_text, ct.explanation
        FROM user_mistakes um
        JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
        JOIN canonical_translations ct ON um.canonical_id = ct.canonical_id AND ct.language = ?
        WHERE um.user_id = ?
        ORDER BY um.mistake_count DESC, um.last_mistake_at DESC
        LIMIT ?
        """, (lang, user_id, min(limit, 10)))
        
        rows = c.fetchall()
        answers_by_cid = {}
        if rows:
            cids = [r["canonical_id"] for r in rows]
            placeholders = ",".join("?" * len(cids))
            c.execute(f"""
                SELECT canonical_id, option_key, {col_text} AS opt_text
                FROM canonical_answers
                WHERE canonical_id IN ({placeholders})
                ORDER BY canonical_id, sort_order
            """, tuple(cids))
            for a in c.fetchall():
                answers_by_cid.setdefault(a["canonical_id"], []).append({"key": a["option_key"], "text": a["opt_text"]})

        results = []
        for idx, r in enumerate(rows):
            rd = dict(r)
            cid = rd["canonical_id"]
            prov = format_legal_provenance_payload(rd)
            results.append({
                "canonical_id": cid,
                "question_number": idx + 1,
                "mistake_count": rd["mistake_count"],
                "category_name": localize_category(rd["category_name"], lang),
                "question": rd["question_text"],
                "explanation": rd["explanation"],
                "correct_option_key": rd["correct_option_key"],
                "options": answers_by_cid.get(cid, []),
                **prov,
            })
            
        return {
            "count": len(results),
            "mistake_questions": results
        }

def tool_get_user_statistics(user_id: int, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining umumiy tayyorgarlik darajasi, imtihonlari, SM-2 takrorlash holati va statistikasini olish."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute("""
        SELECT COUNT(*) as total_exams,
               SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_exams,
               AVG(correct_count) as avg_score,
               AVG(percentage) as avg_percentage
        FROM exam_results
        WHERE user_id = ?
        """, (user_id,))
        exam_stats = c.fetchone()
        
        c.execute("""
        SELECT COUNT(*) as total_bookmarks FROM user_bookmarks WHERE user_id = ?
        """, (user_id,))
        bm_count = c.fetchone()["total_bookmarks"]
        
        c.execute("""
        SELECT COUNT(*) as total_mistakes FROM user_mistakes WHERE user_id = ?
        """, (user_id,))
        mistake_count = c.fetchone()["total_mistakes"]

        srs_tracked = 0
        srs_due_now = 0
        srs_mastered = 0
        try:
            now_ts = datetime.utcnow().isoformat()
            c.execute(
                """
                SELECT COUNT(*) AS tracked_count,
                       COALESCE(SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END), 0) AS due_now_count,
                       COALESCE(SUM(CASE WHEN repetitions >= 3 AND interval_days >= 21 AND ease_factor >= 2.0 THEN 1 ELSE 0 END), 0) AS mastered_count
                FROM user_question_srs
                WHERE user_id = ?
                """,
                (now_ts, user_id),
            )
            srs_row = dict(c.fetchone() or {})
            srs_tracked = int(srs_row.get("tracked_count") or 0)
            srs_due_now = int(srs_row.get("due_now_count") or 0)
            srs_mastered = int(srs_row.get("mastered_count") or 0)
        except Exception:
            pass

        srs_retention = round(((srs_tracked - min(srs_tracked, srs_due_now)) / srs_tracked) * 100.0, 1) if srs_tracked > 0 else 100.0
        
        return {
            "total_exams_taken": exam_stats["total_exams"] or 0,
            "passed_exams": exam_stats["passed_exams"] or 0,
            "average_correct_answers": round(exam_stats["avg_score"] or 0.0, 1),
            "average_percentage": round(exam_stats["avg_percentage"] or 0.0, 1),
            "saved_questions_count": bm_count,
            "mistakes_in_pool": mistake_count,
            "srs_tracked_total": srs_tracked,
            "srs_due_now": srs_due_now,
            "srs_mastered_count": srs_mastered,
            "srs_retention_pct": srs_retention,
        }

def tool_get_srs_review_queue(user_id: int, limit: int = 5, language: str = "uz_latn") -> Dict[str, Any]:
    """Aqlli Takrorlash (SM-2) bo'yicha muddati kelgan yoki eng qiyin savollarni olish."""
    lang = normalize_lang(language)
    safe_limit = max(1, min(int(limit or 5), 10))
    now_ts = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        c = conn.cursor()
        prov_sql = get_provenance_select_sql(conn, "cq")
        try:
            c.execute(
                f"""
                SELECT s.canonical_id, s.ease_factor, s.interval_days, s.repetitions, s.lapses, s.next_review_at,
                       cq.category_name, cq.correct_option_key, cq.legal_reference,
                       {prov_sql},
                       ct.question_text, ct.explanation
                FROM user_question_srs s
                JOIN canonical_questions cq ON s.canonical_id = cq.canonical_id
                LEFT JOIN canonical_translations ct ON s.canonical_id = ct.canonical_id AND ct.language = ?
                WHERE s.user_id = ?
                ORDER BY
                    CASE WHEN s.next_review_at <= ? THEN 0 ELSE 1 END ASC,
                    s.next_review_at ASC,
                    s.ease_factor ASC,
                    s.lapses DESC
                LIMIT ?
                """,
                (lang, user_id, now_ts, safe_limit),
            )
            rows = c.fetchall()
        except Exception:
            rows = []

        items = []
        due_count = 0
        for idx, r in enumerate(rows):
            rd = dict(r)
            is_due = str(rd.get("next_review_at") or "") <= now_ts
            if is_due:
                due_count += 1
            prov = format_legal_provenance_payload(rd)
            items.append({
                "canonical_id": rd["canonical_id"],
                "question_number": idx + 1,
                "category_name": localize_category(rd["category_name"], lang),
                "question": rd["question_text"],
                "explanation": rd["explanation"],
                "correct_option_key": rd["correct_option_key"],
                "ease_factor": round(float(rd.get("ease_factor") or 2.5), 2),
                "interval_days": int(rd.get("interval_days") or 0),
                "lapses": int(rd.get("lapses") or 0),
                "is_due": is_due,
                **prov,
            })

        return {
            "count": len(items),
            "due_count": due_count,
            "srs_items": items,
        }

# Gemini Function Declarations Schema
GEMINI_TOOLS_DECLARATIONS = [
    {
        "name": "search_questions",
        "description": "Avtotest savollar bazasidan berilgan matn, belgi yoki qoida bo'yicha aynan test savolini topish. Faqat foydalanuvchi aniq biror test savolini yoki misolni ko'rsatishni so'raganda ishlatiladi.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Qidirilayotgan kalit so'z, qoida nomi yoki vaziyat (masalan: 'orqaga qayrilish', 'tuman chirog'i', '3.27 belgisi')"
                },
                "category_id": {
                    "type": "INTEGER",
                    "description": "Ixtiyoriy kategoriya id raqami"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Qaytariladigan savollar soni (odatda 1 dan 3 gacha)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_user_bookmarks",
        "description": "Foydalanuvchining saqlangan (bookmark qilingan) savollarini yuklab olish.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "limit": {
                    "type": "INTEGER",
                    "description": "Nechta saqlangan savol olinishi (1 dan 5 gacha)"
                }
            }
        }
    },
    {
        "name": "get_user_mistakes",
        "description": "Foydalanuvchi testlarda eng ko'p adashgan savollarini (xatolarini) yuklab olish.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "limit": {
                    "type": "INTEGER",
                    "description": "Nechta xato savol olinishi (1 dan 5 gacha)"
                }
            }
        }
    },
    {
        "name": "get_user_statistics",
        "description": "Foydalanuvchining umumiy imtihon topshirish tarixi, o'rtacha balli, SM-2 takrorlash darajasi va xatolar sonini yuklash.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "get_srs_review_queue",
        "description": "Talabaning Aqlli Takrorlash (SM-2) jadvalidagi muddati kelgan yoki esda saqlash qiyin bo'lgan savollarni yuklash.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "limit": {
                    "type": "INTEGER",
                    "description": "Olinadigan savollar soni (1 dan 8 gacha)"
                }
            }
        }
    }
]

TOOL_MAPPING = {
    "search_questions": lambda args, uid, lang="uz_latn": tool_search_questions(args.get("query", ""), args.get("category_id"), args.get("limit", 3), language=lang),
    "get_user_bookmarks": lambda args, uid, lang="uz_latn": tool_get_user_bookmarks(uid, args.get("limit", 5), language=lang),
    "get_user_mistakes": lambda args, uid, lang="uz_latn": tool_get_user_mistakes(uid, args.get("limit", 5), language=lang),
    "get_user_statistics": lambda args, uid, lang="uz_latn": tool_get_user_statistics(uid, language=lang),
    "get_srs_review_queue": lambda args, uid, lang="uz_latn": tool_get_srs_review_queue(uid, args.get("limit", 5), language=lang),
}
