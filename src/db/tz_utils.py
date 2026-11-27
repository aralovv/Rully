"""
Shared timezone & subscription evaluation utilities for RULLY Phase 4 repositories.
Standardizes Asia/Tashkent (UTC+5) day boundaries across streaks, daily goals, and AI quotas.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

TASHKENT_TZ = timezone(timedelta(hours=5))


def utc_now_iso() -> str:
    """Returns canonical naive UTC ISO-8601 timestamp string."""
    return datetime.utcnow().isoformat()


def tashkent_now() -> datetime:
    """Returns naive current wall-clock datetime in Asia/Tashkent (UTC+5)."""
    return datetime.now(timezone.utc).astimezone(TASHKENT_TZ).replace(tzinfo=None)


def tashkent_today_str(ref_dt: Optional[datetime] = None) -> str:
    """Returns YYYY-MM-DD in Asia/Tashkent (UTC+5) timezone."""
    dt = ref_dt if ref_dt is not None else tashkent_now()
    return dt.strftime("%Y-%m-%d")


def tashkent_yesterday_str(ref_dt: Optional[datetime] = None) -> str:
    """Returns yesterday's YYYY-MM-DD in Asia/Tashkent (UTC+5) timezone."""
    dt = ref_dt if ref_dt is not None else tashkent_now()
    return (dt - timedelta(days=1)).strftime("%Y-%m-%d")


def parse_iso_dt(raw: Optional[str]) -> Optional[datetime]:
    """Parses stored ISO-8601 timestamps tolerant of trailing 'Z'."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", ""))
    except Exception:
        return None


def evaluate_subscription_row(
    user_row: Optional[Dict[str, Any]],
    now_ts: Optional[str] = None,
    now_dt: Optional[datetime] = None,
) -> Tuple[Dict[str, Any], bool]:
    """
    Computes live subscription payload from a telegram_users row dict.
    Returns (subscription_dict, needs_downgrade_bool).
    """
    default_free = {
        "is_pro": False,
        "tier": "free",
        "tier_name": "Oddiy tarif (Tekin)",
        "expires_at": None,
        "days_left": 0,
        "is_active": False,
    }
    if not user_row:
        return default_free, False

    is_pro = bool(user_row.get("is_pro", 0))
    tier = user_row.get("subscription_tier") or "free"
    sub_exp = user_row.get("subscription_expires_at")
    if not (is_pro and sub_exp):
        return default_free, False

    cur_dt = now_dt or datetime.utcnow()
    cur_ts = now_ts or cur_dt.isoformat()
    exp_dt = parse_iso_dt(sub_exp)
    if exp_dt is not None:
        if exp_dt > cur_dt:
            diff = exp_dt - cur_dt
            days_left = diff.days + (1 if diff.seconds > 0 else 0)
            tier_name = "PRO (14 kunlik)" if "14" in tier else "PRO (30 kunlik)"
            return (
                {
                    "is_pro": True,
                    "tier": tier,
                    "tier_name": tier_name,
                    "expires_at": sub_exp,
                    "days_left": max(1, days_left),
                    "is_active": True,
                },
                False,
            )
        return default_free, True

    if str(sub_exp) > cur_ts:
        tier_name = "PRO (14 kunlik)" if "14" in tier else "PRO (30 kunlik)"
        return (
            {
                "is_pro": True,
                "tier": tier,
                "tier_name": tier_name,
                "expires_at": sub_exp,
                "days_left": 1,
                "is_active": True,
            },
            False,
        )
    return default_free, True


def compute_free_tier_from_counts(subscription: Dict[str, Any], used_exams: int) -> Dict[str, Any]:
    """Builds consistent free-tier exam allowance payload."""
    if subscription.get("is_pro"):
        return {
            "is_pro": True,
            "has_access": True,
            "free_tier_active": False,
            "allowed_exams": 2,
            "used_exams": 0,
            "remaining_exams": 999999,
        }
    remaining = max(0, 2 - max(0, int(used_exams)))
    return {
        "is_pro": False,
        "has_access": remaining > 0,
        "free_tier_active": remaining > 0,
        "allowed_exams": 2,
        "used_exams": int(used_exams),
        "remaining_exams": remaining,
    }
