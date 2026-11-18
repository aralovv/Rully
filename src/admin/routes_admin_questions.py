"""
Admin Question Synchronization & Human-in-the-Loop Moderation Routes.
Provides API endpoints for monitoring external theory question sources (YesPrava, ProPDD),
performing dry-run diff checks, staging new questions for manual inspection,
and manually approving/rejecting/editing questions before committing to production.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.admin.deps import get_current_admin
from src.sync.service import QuestionSyncService

router = APIRouter(prefix="/api/admin/questions", tags=["Admin Questions & Sync"])
sync_service = QuestionSyncService()

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

@router.get("/sync/status")
async def get_sync_status(current_admin: dict = Depends(get_current_admin)) -> Dict[str, Any]:
    """
    Returns live health of external question sources and canonical database metrics.
    """
    try:
        metrics = sync_service.get_database_metrics()
        sources = sync_service.get_all_source_statuses()
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
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Performs an inspection across external sources to detect new questions or amendments.
    If auto_stage=True, stages new questions in the review queue for manual admin approval.
    Does NOT publish directly to production canonical catalog.
    """
    try:
        diff_result = sync_service.check_for_updates(auto_stage=auto_stage)
        return {
            "success": True,
            **diff_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check updates: {str(e)}")

# ================= HUMAN-IN-THE-LOOP STAGING & REVIEW ENDPOINTS =================

@router.get("/staging")
async def list_staged_questions(
    status: str = Query("PENDING_REVIEW"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Lists quarantined/staged questions waiting for admin review.
    """
    try:
        total_pending = sync_service.staging.get_pending_count()
        questions = sync_service.staging.list_staged_questions(status=status, limit=limit, offset=offset)
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
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Approves a staged question and publishes it into the production canonical database.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        res = sync_service.staging.approve_question(staged_id, admin_username=admin_name)
        return {
            "success": True,
            "message": f"Savol muvaffaqiyatli tasdiqlandi va {res['canonical_id']} sifatida bazaga kiritildi.",
            **res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")

@router.post("/staging/{staged_id}/reject")
async def reject_staged_question(
    staged_id: int,
    req: RejectRequest,
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Rejects a staged question. It will NOT be added to production.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        ok = sync_service.staging.reject_question(staged_id, reason=req.reason, admin_username=admin_name)
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
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Applies admin corrections to the staged question, then immediately approves and publishes it.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        edit_data = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
        res = sync_service.staging.edit_and_approve_question(staged_id, edit_data, admin_username=admin_name)
        return {
            "success": True,
            "message": f"Savol tahrirlandi va {res['canonical_id']} sifatida bazaga kiritildi.",
            **res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit and approve failed: {str(e)}")

@router.post("/staging/approve-all")
async def approve_all_staged_questions(
    current_admin: dict = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Batch approves all currently pending questions in the review queue.
    """
    admin_name = current_admin.get("username", "Admin")
    try:
        res = sync_service.staging.approve_all_pending(admin_username=admin_name)
        return {
            "success": True,
            "message": f"{res['approved_count']} ta savol muvaffaqiyatli tasdiqlandi.",
            **res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch approval failed: {str(e)}")
