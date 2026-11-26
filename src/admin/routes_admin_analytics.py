"""
Admin Real Activity & Retention Analytics Routes.
"""

from fastapi import APIRouter, Depends
from src.admin.deps import get_current_admin, require_admin_role
from src.analytics.tracker import get_real_activity_analytics, get_retention_analytics

router = APIRouter(
    prefix="/api/admin/analytics",
    tags=["Admin Activity Analytics"],
    dependencies=[Depends(require_admin_role("FINANCE"))],
)


@router.get("/activity")
def get_activity_analytics(current_admin: dict = Depends(get_current_admin)):
    """Computes DAU, WAU, MAU, engagement ratio, and real feature usage distributions."""
    data = get_real_activity_analytics()
    return {"ok": True, "analytics": data}


@router.get("/retention")
def get_cohort_retention(current_admin: dict = Depends(get_current_admin)):
    """Returns D1, D7, and D30 cohort retention metrics."""
    data = get_retention_analytics()
    return {"ok": True, "retention": data}
