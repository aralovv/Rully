"""
Classified Provenance & Admin Editorial Review Queue Engine (Gate A Decisions U-02 & U-04).

Enforces strict epistemic & legal integrity:
  - Allowed canonical provenance statuses:
      * VERIFIED_PRIMARY_LAW
      * VERIFIED_FIRST_AID_OR_TECH
      * UNRESOLVED_LEGAL_REVIEW
  - Never fabricates legal references from category keywords or heuristics.
  - Quarantines AI-generated drafts strictly as AI_DRAFT_PENDING_REVIEW inside
    editorial_review_queue until a human administrator reviews and approves them.
"""

from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.db.catalog_bundle import bump_catalog_version_sql
from src.db_adapter import execute_batch

ALLOWED_VERIFIED_STATUSES = (
    "VERIFIED_PRIMARY_LAW",
    "VERIFIED_FIRST_AID_OR_TECH",
    "UNRESOLVED_LEGAL_REVIEW",
)

QUEUE_REVIEW_STATUSES = (
    "PENDING_EDITORIAL_REVIEW",
    "AI_DRAFT_PENDING_REVIEW",
    "APPROVED",
    "REJECTED",
)

VMQ_172_DOC_TITLE = "Vazirlar Mahkamasining 2022-yil 12-apreldagi 172-son qarori (YHQ)"
VMQ_172_DOC_URL = "https://lex.uz/docs/5963102"
VMQ_172_EFFECTIVE_DATE = "2022-05-01"

# Explicit Uzbek Latin words/tokens indicating untranslated Uzbek inside a Russian string
_UZ_IN_RU_RE = re.compile(
    r"\b(Eslatma|binoan|asosan|qaroriga|ajratilgan|tasmada|ruxsat\s+etiladi|barcha\s+transport|yo'l\s+belgisi)\b",
    re.IGNORECASE,
)


def _row_dict(row: Any, cols: Optional[List[str]] = None) -> Dict[str, Any]:
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    if cols:
        return dict(zip(cols, row))
    return {}


def audit_and_seed_provenance(conn: Any, admin_actor: str = "system_phase1e_audit") -> Dict[str, Any]:
    """
    Deterministically classifies canonical_questions using U-02 Classified Provenance
    without inventing legal citations or touching user-facing explanation text.
    Enqueues quality/legal gaps idempotently into editorial_review_queue.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_id, category_name, legal_reference, legal_act_title,
               verification_status, legal_verification_status, editorial_reviewed_by
        FROM canonical_questions
        ORDER BY canonical_id
    """)
    q_rows = [_row_dict(r, [d[0] for d in cur.description]) for r in cur.fetchall()]

    cur.execute("""
        SELECT canonical_id, language, question_text, explanation, translation_status
        FROM canonical_translations
        ORDER BY canonical_id, language
    """)
    trans_by_qid: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for r in cur.fetchall():
        rd = _row_dict(r, [d[0] for d in cur.description])
        trans_by_qid.setdefault(rd["canonical_id"], {})[rd["language"]] = rd

    cur.execute("""
        SELECT DISTINCT canonical_id, language
        FROM editorial_review_queue
        WHERE review_status IN ('PENDING_EDITORIAL_REVIEW', 'AI_DRAFT_PENDING_REVIEW')
    """)
    already_queued = {
        (_row_dict(r, ["canonical_id", "language"])["canonical_id"], _row_dict(r, ["canonical_id", "language"])["language"])
        for r in cur.fetchall()
    }

    now_ts = datetime.utcnow().isoformat()
    stmts: List[Any] = []
    counts = {
        "VERIFIED_PRIMARY_LAW": 0,
        "VERIFIED_FIRST_AID_OR_TECH": 0,
        "UNRESOLVED_LEGAL_REVIEW": 0,
        "queued_new_items": 0,
        "already_verified_preserved": 0,
    }
    flag_totals: Dict[str, int] = {}

    for q in q_rows:
        cid = q["canonical_id"]
        existing_cls = q.get("legal_verification_status")
        old_status = q.get("verification_status") or ""
        legal_ref = (q.get("legal_reference") or "").strip()
        cat_name = q.get("category_name") or ""
        langs_map = trans_by_qid.get(cid, {})

        # Never downgrade items already reviewed and approved by a human editor
        if q.get("editorial_reviewed_by") if "editorial_reviewed_by" in q else False:
            target_cls = existing_cls or "UNRESOLVED_LEGAL_REVIEW"
            counts["already_verified_preserved"] += 1
        elif old_status == "LEGAL_CONTENT_MATCHED" and legal_ref:
            target_cls = "VERIFIED_PRIMARY_LAW"
            stmts.append((
                """
                UPDATE canonical_questions
                SET legal_verification_status = 'VERIFIED_PRIMARY_LAW',
                    legal_doc_title = COALESCE(legal_doc_title, ?),
                    legal_doc_url = COALESCE(legal_doc_url, ?),
                    legal_clause = COALESCE(legal_clause, ?),
                    legal_effective_date = COALESCE(legal_effective_date, ?)
                WHERE canonical_id = ?
                """,
                [VMQ_172_DOC_TITLE, VMQ_172_DOC_URL, legal_ref, VMQ_172_EFFECTIVE_DATE, cid],
            ))
            counts["VERIFIED_PRIMARY_LAW"] += 1
        else:
            target_cls = "UNRESOLVED_LEGAL_REVIEW"
            if existing_cls != "UNRESOLVED_LEGAL_REVIEW":
                stmts.append((
                    """
                    UPDATE canonical_questions
                    SET legal_verification_status = 'UNRESOLVED_LEGAL_REVIEW'
                    WHERE canonical_id = ?
                    """,
                    [cid],
                ))
            counts["UNRESOLVED_LEGAL_REVIEW"] += 1

        # Evaluate deterministic issue flags for the Admin Editorial Queue
        issues: List[str] = []
        if not legal_ref:
            issues.append("MISSING_LEGAL_REFERENCE")
        elif legal_ref.lower() == "general yhq scope":
            issues.append("GENERIC_PLACEHOLDER_REF")
        elif target_cls != "VERIFIED_PRIMARY_LAW":
            issues.append("UNVERIFIED_SOURCE_HINT")

        if "birinchi tibbiy" in cat_name.lower() and ("yhq" in legal_ref.lower() or "belgisi" in legal_ref.lower() or "bob" in legal_ref.lower()):
            issues.append("SUSPECT_CATEGORY_LEGAL_MISMATCH")

        for lang_code in ("uz_latn", "uz_cyrl", "ru"):
            tr = langs_map.get(lang_code)
            expl = (tr.get("explanation") or "").strip() if tr else ""
            if not expl:
                issues.append(f"MISSING_EXPLANATION_{lang_code.upper()}")
            elif lang_code == "ru" and _UZ_IN_RU_RE.search(expl):
                issues.append("LANGUAGE_BLEED_UZ_IN_RU")

        for fl in issues:
            flag_totals[fl] = flag_totals.get(fl, 0) + 1

        if issues and (cid, "all") not in already_queued:
            stmts.append((
                """
                INSERT INTO editorial_review_queue (
                    canonical_id, language, draft_legal_status, source_type,
                    review_status, issue_flags_json, created_by, created_at
                ) VALUES (?, 'all', ?, 'AUDIT_FLAG', 'PENDING_EDITORIAL_REVIEW', ?, ?, ?)
                """,
                [cid, target_cls, json.dumps(issues), admin_actor, now_ts],
            ))
            already_queued.add((cid, "all"))
            counts["queued_new_items"] += 1

    # Flush atomically in bounded batches safe for both SQLite and Turso
    for i in range(0, len(stmts), 100):
        execute_batch(conn, stmts[i:i + 100])

    return {
        "total_canonical_evaluated": len(q_rows),
        "classification_counts": counts,
        "issue_flag_totals": flag_totals,
    }


def list_editorial_queue(
    conn: Any,
    status: str = "PENDING_EDITORIAL_REVIEW",
    limit: int = 50,
    offset: int = 0,
    issue_flag: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()

    cur.execute(
        """
        SELECT review_status, COUNT(*) AS cnt
        FROM editorial_review_queue
        GROUP BY review_status
        """
    )
    status_counts = {st: 0 for st in QUEUE_REVIEW_STATUSES}
    for r in cur.fetchall():
        d = _row_dict(r, ["review_status", "cnt"])
        status_counts[str(d["review_status"])] = int(d["cnt"] or 0)

    conditions: List[str] = []
    params: List[Any] = []
    if status and status.upper() != "ALL":
        conditions.append("eq.review_status = ?")
        params.append(status)
    if issue_flag and issue_flag.strip():
        conditions.append("eq.issue_flags_json LIKE ?")
        params.append(f'%"{issue_flag.strip()}"%')
    if q and q.strip():
        like = f"%{q.strip()}%"
        conditions.append("(eq.canonical_id LIKE ? OR cq.category_name LIKE ? OR ct.question_text LIKE ?)")
        params.extend([like, like, like])

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM editorial_review_queue eq
        JOIN canonical_questions cq ON eq.canonical_id = cq.canonical_id
        LEFT JOIN canonical_translations ct ON eq.canonical_id = ct.canonical_id AND ct.language = 'uz_latn'
        {where_sql}
        """,
        tuple(params),
    )
    tot_row = cur.fetchone()
    total = tot_row[0] if not hasattr(tot_row, "values") else list(tot_row.values())[0]

    cur.execute(
        f"""
        SELECT eq.*, cq.category_name, cq.has_image, cq.correct_option_key,
               im.local_path AS image_path,
               cq.legal_reference AS current_legal_hint,
               cq.legal_verification_status AS current_legal_status,
               cq.legal_doc_title AS current_legal_doc_title,
               cq.legal_doc_url AS current_legal_doc_url,
               cq.legal_chapter AS current_legal_chapter,
               cq.legal_clause AS current_legal_clause,
               cq.legal_effective_date AS current_legal_effective_date,
               ct.question_text AS preview_text_uz_latn
        FROM editorial_review_queue eq
        JOIN canonical_questions cq ON eq.canonical_id = cq.canonical_id
        LEFT JOIN images im ON cq.primary_image_id = im.id
        LEFT JOIN canonical_translations ct ON eq.canonical_id = ct.canonical_id AND ct.language = 'uz_latn'
        {where_sql}
        ORDER BY eq.id ASC
        LIMIT ? OFFSET ?
        """,
        tuple(params) + (limit, offset),
    )
    cols = [d[0] for d in cur.description]
    items = []
    canon_ids: List[str] = []
    for r in cur.fetchall():
        d = _row_dict(r, cols)
        try:
            d["issue_flags"] = json.loads(d.get("issue_flags_json") or "[]")
        except Exception:
            d["issue_flags"] = []
        raw_img = d.get("image_path")
        if d.get("has_image") and raw_img:
            fname = str(raw_img).replace("\\", "/").split("/")[-1]
            d["image_url"] = f"/images/{fname}"
        else:
            d["image_url"] = None
        d["translations"] = {}
        d["options"] = []
        canon_ids.append(d["canonical_id"])
        items.append(d)

    if canon_ids:
        unique_ids = sorted(set(canon_ids))
        placeholders = ",".join("?" for _ in unique_ids)
        cur.execute(
            f"""
            SELECT canonical_id, language, question_text, explanation, translation_status
            FROM canonical_translations
            WHERE canonical_id IN ({placeholders})
            """,
            tuple(unique_ids),
        )
        t_cols = [d[0] for d in cur.description]
        trans_map: Dict[str, Dict[str, Any]] = {}
        for tr_row in cur.fetchall():
            tr = _row_dict(tr_row, t_cols)
            trans_map.setdefault(tr["canonical_id"], {})[tr["language"]] = {
                "question_text": tr["question_text"],
                "explanation": tr["explanation"],
                "translation_status": tr["translation_status"],
            }

        cur.execute(
            f"""
            SELECT canonical_id, option_key, is_correct, text_uz_latn, text_uz_cyrl, text_ru
            FROM canonical_answers
            WHERE canonical_id IN ({placeholders})
            ORDER BY canonical_id, sort_order
            """,
            tuple(unique_ids),
        )
        a_cols = [d[0] for d in cur.description]
        ans_map: Dict[str, List[Dict[str, Any]]] = {}
        for a_row in cur.fetchall():
            ar = _row_dict(a_row, a_cols)
            ans_map.setdefault(ar["canonical_id"], []).append({
                "key": ar["option_key"],
                "is_correct": bool(ar["is_correct"]),
                "text_uz_latn": ar["text_uz_latn"],
                "text_uz_cyrl": ar["text_uz_cyrl"],
                "text_ru": ar["text_ru"],
            })

        for d in items:
            d["translations"] = trans_map.get(d["canonical_id"], {})
            d["options"] = ans_map.get(d["canonical_id"], [])

    return {
        "total": total,
        "status": status,
        "status_counts": status_counts,
        "items": items,
    }


def submit_ai_draft(
    conn: Any,
    canonical_id: str,
    language: str,
    draft_explanation: str,
    draft_legal_chapter: Optional[str] = None,
    draft_legal_clause: Optional[str] = None,
    created_by: str = "ai_ustoz_draft",
) -> int:
    """
    Quarantines an AI-generated explanation/citation strictly as AI_DRAFT_PENDING_REVIEW.
    Never modifies canonical_questions or canonical_translations directly.
    """
    if language not in ("uz_latn", "uz_cyrl", "ru"):
        raise ValueError(f"Unsupported language: {language}")
    if not draft_explanation or not draft_explanation.strip():
        raise ValueError("draft_explanation cannot be empty")

    now_ts = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO editorial_review_queue (
            canonical_id, language, draft_explanation, draft_legal_status,
            draft_legal_chapter, draft_legal_clause, source_type, review_status,
            issue_flags_json, created_by, created_at
        ) VALUES (?, ?, ?, 'UNRESOLVED_LEGAL_REVIEW', ?, ?, 'AI_DRAFT', 'AI_DRAFT_PENDING_REVIEW', ?, ?, ?)
        """,
        (
            canonical_id,
            language,
            draft_explanation.strip(),
            draft_legal_chapter,
            draft_legal_clause,
            json.dumps(["AI_GENERATED_REQUIRES_HUMAN_REVIEW"]),
            created_by,
            now_ts,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def approve_editorial_item(
    conn: Any,
    queue_id: int,
    reviewer: str,
    legal_verification_status: str,
    legal_doc_title: Optional[str] = None,
    legal_doc_url: Optional[str] = None,
    legal_chapter: Optional[str] = None,
    legal_clause: Optional[str] = None,
    legal_effective_date: Optional[str] = None,
    approved_explanation: Optional[str] = None,
    explanations_by_lang: Optional[Dict[str, str]] = None,
    question_texts_by_lang: Optional[Dict[str, str]] = None,
    reviewer_notes: str = "Human verified",
) -> Dict[str, Any]:
    """
    Human-in-the-loop approval for editorial queue items.
    Enforces U-02 rule: VERIFIED_PRIMARY_LAW requires non-empty primary document & clause/chapter.
    Commits atomically via execute_batch() and increments catalog_version.
    """
    if legal_verification_status not in ALLOWED_VERIFIED_STATUSES:
        raise ValueError(f"Invalid legal_verification_status: {legal_verification_status}")

    if legal_verification_status == "VERIFIED_PRIMARY_LAW":
        if not (legal_doc_title and legal_doc_title.strip()) or not (
            (legal_chapter and legal_chapter.strip()) or (legal_clause and legal_clause.strip())
        ):
            raise ValueError(
                "VERIFIED_PRIMARY_LAW requires both legal_doc_title and legal_chapter or legal_clause."
            )

    cur = conn.cursor()
    cur.execute("SELECT * FROM editorial_review_queue WHERE id = ?", (queue_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Editorial queue item #{queue_id} not found")
    item = _row_dict(row, [d[0] for d in cur.description])

    cid = item["canonical_id"]
    now_ts = datetime.utcnow().isoformat()
    combined_ref = " — ".join(p for p in (legal_chapter, legal_clause) if p and p.strip()) or None

    stmts: List[Any] = [
        (
            """
            UPDATE canonical_questions
            SET legal_verification_status = ?,
                verification_status = 'ADMIN_MANUALLY_APPROVED',
                legal_doc_title = COALESCE(?, legal_doc_title),
                legal_doc_url = COALESCE(?, legal_doc_url),
                legal_chapter = COALESCE(?, legal_chapter),
                legal_clause = COALESCE(?, legal_clause),
                legal_reference = COALESCE(?, legal_reference),
                legal_effective_date = COALESCE(?, legal_effective_date),
                editorial_reviewed_by = ?,
                editorial_reviewed_at = ?,
                updated_at = datetime('now')
            WHERE canonical_id = ?
            """,
            [
                legal_verification_status,
                legal_doc_title,
                legal_doc_url,
                legal_chapter,
                legal_clause,
                combined_ref,
                legal_effective_date,
                reviewer,
                now_ts,
                cid,
            ],
        )
    ]

    final_expl = approved_explanation.strip() if approved_explanation else None
    if final_expl and item["language"] in ("uz_latn", "uz_cyrl", "ru"):
        stmts.append((
            """
            UPDATE canonical_translations
            SET explanation = ?, translation_status = 'ADMIN_VERIFIED'
            WHERE canonical_id = ? AND language = ?
            """,
            [final_expl, cid, item["language"]],
        ))

    if isinstance(explanations_by_lang, dict):
        for lang_code in ("uz_latn", "uz_cyrl", "ru"):
            val = explanations_by_lang.get(lang_code)
            if val is not None and val.strip():
                stmts.append((
                    """
                    UPDATE canonical_translations
                    SET explanation = ?, translation_status = 'ADMIN_VERIFIED'
                    WHERE canonical_id = ? AND language = ?
                    """,
                    [val.strip(), cid, lang_code],
                ))

    if isinstance(question_texts_by_lang, dict):
        for lang_code in ("uz_latn", "uz_cyrl", "ru"):
            qval = question_texts_by_lang.get(lang_code)
            if qval is not None and qval.strip():
                stmts.append((
                    """
                    UPDATE canonical_translations
                    SET question_text = ?, translation_status = 'ADMIN_VERIFIED'
                    WHERE canonical_id = ? AND language = ?
                    """,
                    [qval.strip(), cid, lang_code],
                ))

    stmts.append((
        """
        UPDATE editorial_review_queue
        SET review_status = 'APPROVED',
            reviewed_by = ?,
            reviewed_at = ?,
            reviewer_notes = ?
        WHERE id = ?
        """,
        [reviewer, now_ts, reviewer_notes, queue_id],
    ))
    stmts.append(bump_catalog_version_sql())

    execute_batch(conn, stmts)
    return {
        "success": True,
        "queue_id": queue_id,
        "canonical_id": cid,
        "legal_verification_status": legal_verification_status,
        "reviewed_by": reviewer,
    }


def reject_editorial_item(conn: Any, queue_id: int, reviewer: str, reason: str = "Rad etildi") -> bool:
    now_ts = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE editorial_review_queue
        SET review_status = 'REJECTED',
            reviewed_by = ?,
            reviewed_at = ?,
            reviewer_notes = ?
        WHERE id = ?
        """,
        (reviewer, now_ts, reason, queue_id),
    )
    conn.commit()
    return cur.rowcount > 0
