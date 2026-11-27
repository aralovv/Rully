"""
Authentication and User Profile Endpoints for RULLY Mini App.
"""

import os
import time
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Tuple
from src.api.deps import get_current_user, get_db, _user_cache
from src.api.security import verify_telegram_init_data, is_production
from src.bot.database import BotDatabase, DEFAULT_SUBSCRIPTION_PLANS
from src.security.rate_limiter import rate_limiter, BoundedTTLCache, get_client_ip

router = APIRouter(prefix="/api", tags=["Auth & User"])

# Ultra-fast bounded in-memory cache for auth bootstrap bundles (max 2000 users, 45s TTL)
_AUTH_BUNDLE_CACHE = BoundedTTLCache[int, Dict[str, Any]](maxsize=2000, ttl_seconds=45.0)

def invalidate_auth_cache(user_id: int):
    _AUTH_BUNDLE_CACHE.pop(user_id, None)
    try:
        from src.api.deps import _user_cache
        _user_cache.pop(user_id, None)
    except Exception:
        pass

class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., description="Raw initData string from Telegram WebApp")

class MiniappBootRequest(BaseModel):
    init_data: Optional[str] = None
    lang: Optional[str] = None

class LanguageUpdateRequest(BaseModel):
    language: str = Field(..., pattern="^(uz_latn|uz_cyrl|ru)$")

class DailyGoalRequest(BaseModel):
    daily_goal: int = Field(..., ge=5, le=100)

class SubscriptionActivateRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID ('pro_14' or 'pro_30')")

@router.post("/auth/telegram")
def auth_telegram(req: TelegramAuthRequest, request: Request, db: BotDatabase = Depends(get_db)):
    client_ip = get_client_ip(request)
    rate_key = f"auth_ip:{client_ip}"
    # IP-based rate limit: 120 req/min (allows shared Wi-Fi NAT environments e.g., driving schools/campuses)
    allowed, _, retry_after = rate_limiter.is_allowed(rate_key, max_requests=120, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many authentication attempts. Please retry in {int(retry_after)}s."
        )

    is_valid, user_data = verify_telegram_init_data(req.init_data)
    if not is_valid or not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user ID")

    # Additional per-user rate limit (max 30 requests/min)
    user_rate_key = f"auth_user:{user_id}"
    allowed_u, _, _ = rate_limiter.is_allowed(user_rate_key, max_requests=30, window_seconds=60)
    if not allowed_u:
        raise HTTPException(status_code=429, detail="Too many authentication requests for this user.")

    cached = _AUTH_BUNDLE_CACHE.get(user_id)
    if cached:
        if int((cached.get("user") or {}).get("is_blocked") or 0) == 1:
            raise HTTPException(status_code=403, detail="USER_BLOCKED: Sizning hisobingiz bloklangan.")
        if cached.get("user"):
            _user_cache.set(user_id, cached["user"])
        return {
            "ok": True,
            **cached
        }

    bundle = db.get_user_full_auth_bundle(
        user_id=user_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name", "Haydovchi"),
        last_name=user_data.get("last_name", "")
    )

    _AUTH_BUNDLE_CACHE.set(user_id, bundle)
    if bundle.get("user"):
        _user_cache.set(user_id, bundle["user"])
    if int((bundle.get("user") or {}).get("is_blocked") or 0) == 1:
        raise HTTPException(status_code=403, detail="USER_BLOCKED: Sizning hisobingiz bloklangan.")

    return {
        "ok": True,
        **bundle
    }

@router.post("/miniapp/boot")
def miniapp_boot(
    req: Optional[MiniappBootRequest] = Body(default=None),
    request: Request = None,
    db: BotDatabase = Depends(get_db),
):
    """
    Zero-waterfall Mini App startup endpoint (<= 2 Turso RTs).
    Authenticates Telegram initData (or dev user offline), populates auth/user caches,
    and returns user + subscription + stats + UTC+5 streak + history + analytics + categories + AI usage.
    """
    init_data = (req.init_data if req else None) or (request.headers.get("X-Telegram-Init-Data") if request else None)
    user_meta: Dict[str, Any] = {}
    if not init_data or str(init_data).strip().lower() in ("null", "undefined", "none", ""):
        if is_production():
            raise HTTPException(status_code=401, detail="Missing Telegram authentication data")
        user_id = 8809526955
        user_meta = {"username": "kurs_savdo", "first_name": "RULLY User", "last_name": ""}
    else:
        is_valid, user_data = verify_telegram_init_data(init_data)
        if not is_valid or not user_data or not user_data.get("id"):
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")
        user_id = int(user_data["id"])
        user_meta = user_data

    from src.api.routes_theory import engine
    req_lang = (req.lang if req else None)
    selected_lang = req_lang if req_lang in ("uz_latn", "uz_cyrl", "ru") else None

    # Fetch user's stored language if not explicitly passed, or fall back cleanly after bundle load
    cats_lang = selected_lang or "uz_latn"
    cats = engine.get_categories(cats_lang)
    total_q = engine.get_total_question_count()

    bundle = db.get_user_full_auth_bundle(
        user_id=user_id,
        username=user_meta.get("username"),
        first_name=user_meta.get("first_name", "Haydovchi"),
        last_name=user_meta.get("last_name", ""),
        categories=cats,
        engine_total_questions=total_q,
    )
    user_obj = bundle.get("user") or {}
    if int(user_obj.get("is_blocked") or 0) == 1:
        raise HTTPException(status_code=403, detail="USER_BLOCKED: Sizning hisobingiz bloklangan.")

    # Localize categories accurately if user's saved language differs from default uz_latn
    actual_lang = selected_lang or user_obj.get("language") or "uz_latn"
    if actual_lang in ("uz_cyrl", "ru") and actual_lang != cats_lang:
        cats = engine.get_categories(actual_lang)
        cat_name_map = {int(c["category_id"]): c["name"] for c in cats}
        for cm in (bundle.get("analytics") or {}).get("category_mastery", []):
            cm["name"] = cat_name_map.get(int(cm["category_id"]), cm["name"])
        for bucket in ("weak_categories", "strong_categories"):
            for cm in (bundle.get("analytics") or {}).get(bucket, []):
                cm["name"] = cat_name_map.get(int(cm["category_id"]), cm["name"])
        rec = (bundle.get("analytics") or {}).get("recommendation") or {}
        if rec.get("target_id") is not None and int(rec["target_id"]) in cat_name_map:
            rec["topic_name"] = cat_name_map[int(rec["target_id"])]

    _AUTH_BUNDLE_CACHE.set(user_id, bundle)
    if user_obj:
        _user_cache.set(user_id, user_obj)

    return {
        "ok": True,
        "language": actual_lang,
        "total_questions": total_q,
        "total_categories": len(cats),
        "categories": cats,
        **bundle,
    }

@router.get("/user/me")
def get_user_me(user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    bundle = db.get_user_full_auth_bundle(user_id=user["user_id"])
    return {
        "user": bundle["user"],
        "subscription": bundle["subscription"],
        "free_tier": bundle["free_tier"],
        "stats": bundle["stats"],
        "streak": bundle["streak"],
        "bookmarks_count": bundle["bookmarks_count"],
        "history": bundle["history"],
    }

@router.post("/user/language")
def set_language(req: LanguageUpdateRequest, user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    user_id = user["user_id"]
    db.set_user_language(user_id, req.language)
    invalidate_auth_cache(user_id)
    return {"ok": True, "language": req.language}

@router.post("/user/daily-goal")
def set_daily_goal(req: DailyGoalRequest, user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    user_id = user["user_id"]
    updated = db.set_daily_goal(user_id, req.daily_goal)
    invalidate_auth_cache(user_id)
    return {"ok": True, "daily_goal_questions": updated}

# --- Subscription API Endpoints ---
@router.get("/subscription/plans")
def get_subscription_plans():
    try:
        from src.payments.order_manager import list_active_subscription_plans
        plans = list_active_subscription_plans()
        if plans:
            return {"plans": plans}
    except Exception:
        pass
    return {
        "plans": list(DEFAULT_SUBSCRIPTION_PLANS.values())
    }

@router.get("/subscription/status")
def get_subscription_status(user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    sub = db.get_user_subscription(user["user_id"])
    ft = db.get_user_free_tier_status(user["user_id"], subscription=sub)
    return {"ok": True, "subscription": sub, "free_tier": ft}

@router.post("/subscription/activate")
def activate_subscription(
    req: SubscriptionActivateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    # Security (P0): Fail-closed. Direct manual activation is strictly forbidden in production / live cloud.
    allow_test = os.getenv("ALLOW_TEST_ACTIVATION", "").strip().lower() == "true"
    is_cloud_prod = bool(os.getenv("VERCEL") or os.getenv("RENDER") or os.getenv("ENVIRONMENT", "").lower() in ["production", "prod"])
    if not allow_test or is_cloud_prod:
        raise HTTPException(
            status_code=403,
            detail="DIRECT_ACTIVATION_DISABLED: Manual activation is disabled in production. Please use /api/payment/orders/create"
        )

    user_id = user["user_id"]
    sub = db.activate_subscription(user_id, req.plan_id)
    invalidate_auth_cache(user_id)
    return {
        "ok": True,
        "subscription": sub,
        "message": "PRO tarif muvaffaqiyatli faollashtirildi!"
    }
