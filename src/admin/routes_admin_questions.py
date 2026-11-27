"""
Admin Question Synchronization & Human-in-the-Loop Moderation Routes.
Provides API endpoints for monitoring external theory question sources (YesPrava, ProPDD),
performing dry-run diff checks, staging new questions for manual inspection,
and manually approving/rejecting/editing questions before committing to production.
"""
import asyncio
import hmac
import logging
import os
import re
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin, require_admin_role
from src.api.routes_theory import invalidate_theory_caches
from src.db.catalog_bundle import trigger_vercel_deploy_hook, write_canonical_bundle_atomic
from src.db.provenance_classifier import (
    approve_editorial_item,
    audit_and_seed_provenance,
    bulk_approve_editorial_items_batched,
    bulk_reject_editorial_items,
    list_editorial_queue,
    reject_editorial_item,
    submit_ai_draft,
)
from src.db_adapter import get_db_connection
from src.sync.service import QuestionSyncService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/questions", tags=["Admin Questions & Sync"])
sync_service = QuestionSyncService()


def _invalidate_after_catalog_write(reason: str):
    """Evicts in-memory engine/category caches immediately, refreshes local bundle if canonical, and triggers optional Vercel deploy hook."""
    if not os.getenv("VERCEL") and os.path.abspath(sync_service.db_path) == os.path.abspath("master_database.sqlite"):
        try:
            with get_db_connection(sync_service.db_path) as conn:
                write_canonical_bundle_atomic(conn, out_dir="data")
        except Exception as exc:
            logger.warning("Failed refreshing canonical_bundle after catalog write (%s): %s", reason, exc)
    invalidate_theory_caches(reload_engine=True)
    trigger_vercel_deploy_hook(reason=reason)

class SyncRunRequest(BaseModel):
    source: Optional[str] = "all"  # all, yesprava, propdd
    ticket: Optional[int] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = "Admin tomonidan rad etildi"

class EditStagedRequest(BaseModel):
    text_uz_latn: Optional[str] = None
    text_uz_cyrl: Optional[str] = None
    text_ru: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    correct_option_key: Optional[str] = None
    explanation: Optional[str] = None
    explanation_uz_latn: Optional[str] = None
    explanation_uz_cyrl: Optional[str] = None
    explanation_ru: Optional[str] = None
    legal_verification_status: Optional[str] = None
    legal_doc_title: Optional[str] = None
    legal_doc_url: Optional[str] = None
    legal_chapter: Optional[str] = None
    legal_clause: Optional[str] = None
    legal_effective_date: Optional[str] = None

@router.get("/sync/status")
async def get_sync_status(current_admin: dict = Depends(require_admin_role("MODERATOR"))) -> Dict[str, Any]:
    """
    Returns live health of external question sources and canonical database metrics.
    """
    try:
        metrics, sources = await asyncio.gather(
            asyncio.to_thread(sync_service.get_database_metrics),
            asyncio.to_thread(sync_service.get_all_source_statuses),
        )
        return {
            "success": True,
            "database": metrics,
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sync status: {str(e)}")

@router.post("/sync/check")
async def check_sync_updates(
    auto_stage: bool = Query(True),
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Performs an inspection across external sources to detect new questions or amendments.
    If auto_stage=True, stages new questions in the review queue for manual admin approval.
    Does NOT publish directly to production canonical catalog.
    """
    try:
        diff_result = await asyncio.to_thread(sync_service.check_for_updates, auto_stage=auto_stage)
        return {
            "success": True,
            **diff_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check updates: {str(e)}")

@router.post("/sync/webhook")
async def scheduled_sync_webhook(
    auto_stage: bool = Query(True),
    x_sync_secret: Optional[str] = Header(None, alias="X-Sync-Secret"),
) -> Dict[str, Any]:
    """
    Fail-closed scheduled webhook entrypoint for GitHub Actions offloaded source scraping (U-03).
    Never runs without SYNC_WEBHOOK_SECRET configured and matched via constant-time comparison.
    """
    expected = os.getenv("SYNC_WEBHOOK_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="SYNC_WEBHOOK_SECRET not configured on server.")
    if not x_sync_secret or not hmac.compare_digest(x_sync_secret.strip(), expected):
        raise HTTPException(status_code=403, detail="Invalid X-Sync-Secret header.")

    diff_result = await asyncio.to_thread(sync_service.check_for_updates, auto_stage=auto_stage)
    return {
        "success": True,
        **diff_result,
    }


# ================= HUMAN-IN-THE-LOOP STAGING & REVIEW ENDPOINTS =================

@router.get("/staging")
async def list_staged_questions(
    status: str = Query("PENDING_REVIEW"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Lists quarantined/staged questions waiting for admin review.
    """
    try:
        total_pending, questions = await asyncio.gather(
            asyncio.to_thread(sync_service.staging.get_pending_count),
            asyncio.to_thread(sync_service.staging.list_staged_questions, status=status, limit=limit, offset=offset),
        )
        return {
            "success": True,
            "status": status,
            "total_pending": total_pending,
            "count": len(questions),
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load staging queue: {str(e)}")

@router.post("/staging/{staged_id}/approve")
async def approve_staged_question(
    staged_id: int,
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Approves a staged question and publishes it into the production canonical database.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        res = await asyncio.to_thread(sync_service.staging.approve_question, staged_id, admin_username=admin_name)
        await asyncio.to_thread(_invalidate_after_catalog_write, f"staged_approve:{staged_id}")
        return {
            "success": True,
            "message": f"Savol muvaffaqiyatli tasdiqlandi va {res['canonical_id']} sifatida bazaga kiritildi.",
            **res
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")

@router.post("/staging/{staged_id}/reject")
async def reject_staged_question(
    staged_id: int,
    req: RejectRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Rejects a staged question. It will NOT be added to production.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        ok = await asyncio.to_thread(sync_service.staging.reject_question, staged_id, reason=req.reason, admin_username=admin_name)
        if not ok:
            raise HTTPException(status_code=404, detail="Staged question not found.")
        return {
            "success": True,
            "message": f"Savol #{staged_id} rad etildi."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")

@router.post("/staging/{staged_id}/edit")
async def edit_and_approve_staged_question(
    staged_id: int,
    req: EditStagedRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Applies admin corrections to the staged question, then immediately approves and publishes it.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        edit_data = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
        res = await asyncio.to_thread(sync_service.staging.edit_and_approve_question, staged_id, edit_data, admin_username=admin_name)
        await asyncio.to_thread(_invalidate_after_catalog_write, f"staged_edit_approve:{staged_id}")
        return {
            "success": True,
            "message": f"Savol tahrirlandi va {res['canonical_id']} sifatida bazaga kiritildi.",
            **res
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit and approve failed: {str(e)}")

@router.post("/staging/approve-all")
async def approve_all_staged_questions(
    current_admin: dict = Depends(require_admin_role("MODERATOR"))
) -> Dict[str, Any]:
    """
    Batch approves all currently pending questions in the review queue.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        res = await asyncio.to_thread(sync_service.staging.approve_all_pending, admin_username=admin_name)
        if res.get("approved_count", 0) > 0:
            await asyncio.to_thread(_invalidate_after_catalog_write, "staged_approve_all")
        return {
            "success": True,
            "message": f"{res['approved_count']} ta savol muvaffaqiyatli tasdiqlandi.",
            **res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch approval failed: {str(e)}")


# ================= CLASSIFIED PROVENANCE & ADMIN EDITORIAL QUEUE (U-02 / U-04) =================

class SubmitAIDraftRequest(BaseModel):
    canonical_id: str
    language: str
    draft_explanation: str
    draft_legal_chapter: Optional[str] = None
    draft_legal_clause: Optional[str] = None


class ApproveEditorialRequest(BaseModel):
    legal_verification_status: str
    legal_doc_title: Optional[str] = None
    legal_doc_url: Optional[str] = None
    legal_chapter: Optional[str] = None
    legal_clause: Optional[str] = None
    legal_effective_date: Optional[str] = None
    approved_explanation: Optional[str] = None
    explanations_by_lang: Optional[Dict[str, str]] = None
    question_texts_by_lang: Optional[Dict[str, str]] = None
    reviewer_notes: str = "Human verified"


@router.get("/editorial")
async def get_editorial_queue(
    status: str = Query("PENDING_EDITORIAL_REVIEW"),
    issue_flag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return list_editorial_queue(conn, status=status, limit=limit, offset=offset, issue_flag=issue_flag, q=q, source_type=source_type)

    try:
        data = await asyncio.to_thread(_run)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Editorial queue load failed: {str(e)}")


@router.post("/editorial/audit-seed")
async def seed_editorial_audit(
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return audit_and_seed_provenance(conn, admin_actor=admin_name)

    try:
        res = await asyncio.to_thread(_run)
        return {"success": True, **res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Editorial audit seed failed: {str(e)}")


@router.post("/editorial/submit-ai-draft")
async def quarantine_ai_draft(
    req: SubmitAIDraftRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return submit_ai_draft(
                conn,
                canonical_id=req.canonical_id,
                language=req.language,
                draft_explanation=req.draft_explanation,
                draft_legal_chapter=req.draft_legal_chapter,
                draft_legal_clause=req.draft_legal_clause,
                created_by=f"ai_draft_via_{admin_name}",
            )

    try:
        qid = await asyncio.to_thread(_run)
        return {
            "success": True,
            "queue_id": qid,
            "review_status": "AI_DRAFT_PENDING_REVIEW",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft submission failed: {str(e)}")


class BulkApproveEditorialRequest(BaseModel):
    queue_ids: List[int] = Field(..., min_length=1, max_length=50)
    legal_verification_status: str = "VERIFIED_FIRST_AID_OR_TECH"
    legal_doc_title: Optional[str] = None
    legal_doc_url: Optional[str] = None
    legal_chapter: Optional[str] = None
    legal_clause: Optional[str] = None
    reviewer_notes: str = "Bulk human verified"


@router.post("/editorial/{queue_id}/approve")
async def approve_editorial_queue_item(
    queue_id: int,
    req: ApproveEditorialRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return approve_editorial_item(
                conn,
                queue_id=queue_id,
                reviewer=admin_name,
                legal_verification_status=req.legal_verification_status,
                legal_doc_title=req.legal_doc_title,
                legal_doc_url=req.legal_doc_url,
                legal_chapter=req.legal_chapter,
                legal_clause=req.legal_clause,
                legal_effective_date=req.legal_effective_date,
                approved_explanation=req.approved_explanation,
                explanations_by_lang=req.explanations_by_lang,
                question_texts_by_lang=req.question_texts_by_lang,
                reviewer_notes=req.reviewer_notes,
            )

    try:
        res = await asyncio.to_thread(_run)
        await asyncio.to_thread(_invalidate_after_catalog_write, f"editorial_approve:{queue_id}")
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Editorial approval failed: {str(e)}")


@router.post("/editorial/bulk-approve")
async def bulk_approve_editorial_items(
    req: BulkApproveEditorialRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return bulk_approve_editorial_items_batched(
                conn,
                queue_ids=req.queue_ids,
                reviewer=admin_name,
                legal_verification_status=req.legal_verification_status,
                legal_doc_title=req.legal_doc_title,
                legal_doc_url=req.legal_doc_url,
                legal_chapter=req.legal_chapter,
                legal_clause=req.legal_clause,
                reviewer_notes=req.reviewer_notes,
            )

    try:
        out = await asyncio.to_thread(_run)
        if out["approved"]:
            await asyncio.to_thread(_invalidate_after_catalog_write, f"editorial_bulk:{len(out['approved'])}")
        return {"success": True, **out}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk approval failed: {str(e)}")


@router.post("/editorial/{queue_id}/ai-draft")
async def generate_ai_editorial_draft(
    queue_id: int,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    """Generates a quarantined 3-language AI explanation draft without touching canonical tables."""
    from src.ai.gemini_service import GeminiService
    import json as _json

    def _load_item():
        with get_db_connection(sync_service.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT canonical_id FROM editorial_review_queue WHERE id = ?", (queue_id,))
            row = cur.fetchone()
            if not row:
                return None
            cid = row[0] if not hasattr(row, "keys") else row["canonical_id"]
            cur.execute("SELECT correct_option_key, legal_reference, category_name FROM canonical_questions WHERE canonical_id = ?", (cid,))
            q_row = cur.fetchone()
            cur.execute("SELECT language, question_text, explanation FROM canonical_translations WHERE canonical_id = ?", (cid,))
            trans = {(r[0] if not hasattr(r, "keys") else r["language"]): (r[1] if not hasattr(r, "keys") else r["question_text"]) for r in cur.fetchall()}
            cur.execute("SELECT option_key, text_uz_latn FROM canonical_answers WHERE canonical_id = ? ORDER BY sort_order", (cid,))
            opts = { (r[0] if not hasattr(r, "keys") else r["option_key"]): (r[1] if not hasattr(r, "keys") else r["text_uz_latn"]) for r in cur.fetchall() }
            ckey = (q_row[0] if q_row and not hasattr(q_row, "keys") else (q_row["correct_option_key"] if q_row else ""))
            return {
                "canonical_id": cid,
                "correct_option_key": ckey,
                "correct_option_text": opts.get(ckey, ""),
                "legal_reference": (q_row[1] if q_row and not hasattr(q_row, "keys") else (q_row["legal_reference"] if q_row else "")),
                "question_text": trans.get("uz_latn") or "",
                "question_text_cyrl": trans.get("uz_cyrl") or "",
                "question_text_ru": trans.get("ru") or "",
            }

    item = await asyncio.to_thread(_load_item)
    if not item:
        raise HTTPException(status_code=404, detail="Editorial queue item not found")

    ai = GeminiService()
    if not ai.api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY configured emas; AI draft yaratib bo‘lmadi.")

    prompt = (
        f"Savol (UZ Lotin): {item['question_text']}\n"
        f"Savol (UZ Kirill): {item['question_text_cyrl']}\n"
        f"Вопрос (RU): {item['question_text_ru']}\n"
        f"To'g'ri variant: {item['correct_option_key']} ({item['correct_option_text']})\n"
        f"Mavjud havola: {item['legal_reference'] or 'koʻrsatilmagan'}\n"
        "O'zbekiston YHQ asosida 3 tilda (uz_latn, uz_cyrl, ru) qisqa va aniq tushuntirish yozing. "
        "Agar aniq band ko'rsatilmagan bo'lsa, band raqamini o'ylab topmang. "
        'Faqat JSON qaytaring: {"uz_latn":"...","uz_cyrl":"...","ru":"..."}'
    )
    import httpx
    async with httpx.AsyncClient(timeout=25.0) as client:
        data, status_code, err = await ai._call_gemini_with_fallback(
            client,
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.25, "maxOutputTokens": 1200, "responseMimeType": "application/json"},
            },
        )
    if not data or status_code != 200:
        raise HTTPException(status_code=502, detail=f"AI draft generation failed: {err or status_code}")

    raw_txt = "".join(
        p.get("text", "")
        for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        if isinstance(p, dict) and not p.get("thought")
    ).strip()
    cleaned_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_txt, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = _json.loads(cleaned_json)
        drafts = {
            "uz_latn": str(parsed.get("uz_latn") or "").strip(),
            "uz_cyrl": str(parsed.get("uz_cyrl") or "").strip(),
            "ru": str(parsed.get("ru") or "").strip(),
        }
    except Exception:
        logger.warning("Editorial AI draft JSON parse fallback for %s", item["canonical_id"])
        drafts = {"uz_latn": raw_txt, "uz_cyrl": "", "ru": ""}

    actor = f"ai_draft_panel_{current_admin.get('username', 'Admin')}"

    def _quarantine():
        saved_qids: Dict[str, int] = {}
        with get_db_connection(sync_service.db_path) as conn:
            for lang_code in ("uz_latn", "uz_cyrl", "ru"):
                txt = (drafts.get(lang_code) or "").strip()
                if txt:
                    saved_qids[lang_code] = submit_ai_draft(
                        conn,
                        canonical_id=item["canonical_id"],
                        language=lang_code,
                        draft_explanation=txt,
                        created_by=actor,
                    )
        return saved_qids.get("uz_latn") or next(iter(saved_qids.values()), None)

    draft_qid = await asyncio.to_thread(_quarantine)
    if draft_qid is None:
        raise HTTPException(status_code=502, detail="AI bo‘sh qoralama qaytardi; iltimos, qayta urinib ko‘ring.")
    return {"success": True, "queue_id": draft_qid, "canonical_id": item["canonical_id"], "drafts": drafts}


@router.post("/editorial/{queue_id}/reject")
async def reject_editorial_queue_item(
    queue_id: int,
    req: RejectRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return reject_editorial_item(conn, queue_id=queue_id, reviewer=admin_name, reason=req.reason or "Rad etildi")

    ok = await asyncio.to_thread(_run)
    if not ok:
        raise HTTPException(status_code=404, detail="Editorial queue item not found.")
    return {"success": True, "queue_id": queue_id, "review_status": "REJECTED"}


class BulkRejectEditorialRequest(BaseModel):
    queue_ids: List[int] = Field(..., min_length=1, max_length=200)
    reason: str = "Bulk rejected"


@router.post("/editorial/bulk-reject")
async def bulk_reject_editorial_items_endpoint(
    req: BulkRejectEditorialRequest,
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    admin_name = current_admin.get("username", "Admin")

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return bulk_reject_editorial_items(conn, queue_ids=req.queue_ids, reviewer=admin_name, reason=req.reason)

    try:
        out = await asyncio.to_thread(_run)
        return {"success": True, **out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk rejection failed: {str(e)}")


@router.get("/catalog/status")
async def get_catalog_status(
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    """Returns current canonical bundle metadata and queue summary for catalog health monitoring."""
    import json as _json

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'catalog_version'")
            ver_row = cur.fetchone()
            version = int((ver_row[0] if not hasattr(ver_row, "keys") else ver_row["value"]) or 0) if ver_row else 0

            cur.execute("SELECT review_status, COUNT(*) AS cnt FROM editorial_review_queue GROUP BY review_status")
            queue_counts: Dict[str, int] = {}
            for r in cur.fetchall():
                d = r if hasattr(r, "keys") else {"review_status": r[0], "cnt": r[1]}
                queue_counts[str(d["review_status"] if hasattr(d, "keys") else r[0])] = int(d["cnt"] if hasattr(d, "keys") else r[1])

            cur.execute("SELECT COUNT(*) FROM canonical_questions")
            r_tot = cur.fetchone()
            q_total = int(list(r_tot.values())[0] if hasattr(r_tot, "values") else r_tot[0])
            cur.execute("SELECT COUNT(*) FROM canonical_questions WHERE legal_verification_status = 'VERIFIED_PRIMARY_LAW'")
            r_ver = cur.fetchone()
            q_verified = int(list(r_ver.values())[0] if hasattr(r_ver, "values") else r_ver[0])

        bundle_path = "data/canonical_bundle.json"
        bundle_meta: Dict[str, Any] = {}
        try:
            if os.path.exists(bundle_path):
                with open(bundle_path, "r", encoding="utf-8") as f:
                    raw = _json.load(f)
                bundle_meta = {
                    "canonical_count": raw.get("canonical_count"),
                    "db_catalog_revision": raw.get("db_catalog_revision"),
                    "payload_sha256": raw.get("payload_sha256"),
                }
        except Exception as exc:
            logger.warning("Failed reading canonical_bundle.json metadata: %s", exc)

        return {
            "catalog_version": version,
            "canonical_total": q_total,
            "canonical_verified_law": q_verified,
            "queue_counts": queue_counts,
            "bundle": bundle_meta,
        }

    try:
        data = await asyncio.to_thread(_run)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Catalog status check failed: {str(e)}")


@router.post("/catalog/rebuild")
async def rebuild_catalog_bundle(
    current_admin: dict = Depends(require_admin_role("MODERATOR")),
) -> Dict[str, Any]:
    """Force-rebuilds the canonical bundle JSON and invalidates all caches. Use after bulk edits."""
    is_main_db = os.path.abspath(sync_service.db_path) == os.path.abspath("master_database.sqlite")
    out_dir = "data" if is_main_db else os.path.dirname(os.path.abspath(sync_service.db_path))

    def _run():
        with get_db_connection(sync_service.db_path) as conn:
            return write_canonical_bundle_atomic(conn, out_dir=out_dir)

    try:
        result = await asyncio.to_thread(_run)
        invalidate_theory_caches(reload_engine=True)
        if is_main_db:
            await asyncio.to_thread(trigger_vercel_deploy_hook, reason="manual_rebuild")
        return {"success": True, "bundle": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Catalog rebuild failed: {str(e)}")
