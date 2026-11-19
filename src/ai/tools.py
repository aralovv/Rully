import json
from typing import List, Dict, Any, Optional
from src.db_adapter import get_db_connection
from src.bot.category_localization import localize_category

def normalize_lang(language: Optional[str]) -> str:
    lang = (language or "uz_latn").lower().strip()
    if lang in ("ru", "russian"):
        return "ru"
    if lang in ("uz_cyrl", "cyrl", "kirill"):
        return "uz_cyrl"
    return "uz_latn"

def tool_search_questions(
    query: str,
    category_id: Optional[int] = None,
    limit: int = 3,
    language: str = "uz_latn"
) -> Dict[str, Any]:
    """1295 ta savol ichidan qidirish (savol matni, izohi yoki qonuniy havolasi bo‘yicha)."""
    conn = get_db_connection()
    c = conn.cursor()
    
    lang = normalize_lang(language)
    col_text = f"text_{lang}"
    q_pattern = f"%{query}%"
    
    cat_sql = ""
    params = [lang, q_pattern, q_pattern, q_pattern]
    if category_id is not None:
        cat_sql = " AND cq.category_id = ? "
        params.append(category_id)
        
    params.append(min(limit, 5))
    
    sql = f"""
    SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.correct_option_key, cq.legal_reference,
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
    
    results = []
    for idx, r in enumerate(rows):
        cid = r["canonical_id"]
        c.execute(f"""
            SELECT option_key, {col_text} AS opt_text
            FROM canonical_answers
            WHERE canonical_id = ?
            ORDER BY sort_order
        """, (cid,))
        answers = [{"key": a["option_key"], "text": a["opt_text"]} for a in c.fetchall()]
        
        results.append({
            "canonical_id": cid,
            "question_number": idx + 1,
            "category_name": localize_category(r["category_name"], lang),
            "question": r["question_text"],
            "legal_reference": r["legal_reference"],
            "explanation": r["explanation"],
            "correct_option_key": r["correct_option_key"],
            "options": answers
        })
        
    return {
        "count": len(results),
        "questions": results
    }

def tool_get_user_bookmarks(user_id: int, limit: int = 5, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining saqlangan (bookmark) savollarini olish."""
    conn = get_db_connection()
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
    results = []
    for idx, r in enumerate(rows):
        cid = r["canonical_id"]
        c.execute(f"""
            SELECT option_key, {col_text} AS opt_text
            FROM canonical_answers
            WHERE canonical_id = ?
            ORDER BY sort_order
        """, (cid,))
        answers = [{"key": a["option_key"], "text": a["opt_text"]} for a in c.fetchall()]
        
        results.append({
            "canonical_id": cid,
            "question_number": idx + 1,
            "category_name": localize_category(r["category_name"], lang),
            "question": r["question_text"],
            "legal_reference": r["legal_reference"],
            "explanation": r["explanation"],
            "correct_option_key": r["correct_option_key"],
            "options": answers
        })
        
    return {
        "count": len(results),
        "saved_questions": results
    }

def tool_get_user_mistakes(user_id: int, limit: int = 5, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining testlarda adashgan (xato qilgan) savollarini olish."""
    conn = get_db_connection()
    c = conn.cursor()
    
    lang = normalize_lang(language)
    col_text = f"text_{lang}"
    
    c.execute("""
    SELECT um.canonical_id, um.mistake_count, cq.category_name, cq.correct_option_key, cq.legal_reference,
           ct.question_text, ct.explanation
    FROM user_mistakes um
    JOIN canonical_questions cq ON um.canonical_id = cq.canonical_id
    JOIN canonical_translations ct ON um.canonical_id = ct.canonical_id AND ct.language = ?
    WHERE um.user_id = ?
    ORDER BY um.mistake_count DESC, um.last_mistake_at DESC
    LIMIT ?
    """, (lang, user_id, min(limit, 10)))
    
    rows = c.fetchall()
    results = []
    for idx, r in enumerate(rows):
        cid = r["canonical_id"]
        c.execute(f"""
            SELECT option_key, {col_text} AS opt_text
            FROM canonical_answers
            WHERE canonical_id = ?
            ORDER BY sort_order
        """, (cid,))
        answers = [{"key": a["option_key"], "text": a["opt_text"]} for a in c.fetchall()]
        
        results.append({
            "canonical_id": cid,
            "question_number": idx + 1,
            "mistake_count": r["mistake_count"],
            "category_name": localize_category(r["category_name"], lang),
            "question": r["question_text"],
            "legal_reference": r["legal_reference"],
            "explanation": r["explanation"],
            "correct_option_key": r["correct_option_key"],
            "options": answers
        })
        
    return {
        "count": len(results),
        "mistake_questions": results
    }

def tool_get_user_statistics(user_id: int, language: str = "uz_latn") -> Dict[str, Any]:
    """Foydalanuvchining umumiy tayyorgarlik darajasi, imtihonlari va statistikasini olish."""
    conn = get_db_connection()
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
    
    return {
        "total_exams_taken": exam_stats["total_exams"] or 0,
        "passed_exams": exam_stats["passed_exams"] or 0,
        "average_correct_answers": round(exam_stats["avg_score"] or 0.0, 1),
        "average_percentage": round(exam_stats["avg_percentage"] or 0.0, 1),
        "saved_questions_count": bm_count,
        "mistakes_in_pool": mistake_count
    }

# Gemini Function Declarations Schema
GEMINI_TOOLS_DECLARATIONS = [
    {
        "name": "search_questions",
        "description": "Avtotest savollar bazasidan berilgan matn, belgi yoki qoida bo'yicha tegishli savollarni qidirish.",
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
        "description": "Foydalanuvchining umumiy imtihon topshirish tarixi, o'rtacha balli va xatolar sonini yuklash.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    }
]

TOOL_MAPPING = {
    "search_questions": lambda args, uid, lang="uz_latn": tool_search_questions(args.get("query", ""), args.get("category_id"), args.get("limit", 3), language=lang),
    "get_user_bookmarks": lambda args, uid, lang="uz_latn": tool_get_user_bookmarks(uid, args.get("limit", 5), language=lang),
    "get_user_mistakes": lambda args, uid, lang="uz_latn": tool_get_user_mistakes(uid, args.get("limit", 5), language=lang),
    "get_user_statistics": lambda args, uid, lang="uz_latn": tool_get_user_statistics(uid, language=lang)
}
