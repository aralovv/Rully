"""
Authentication and User Profile Endpoints for RULLY Mini App.
"""

import os
import time
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Tuple
from src.api.deps import get_current_user, get_db
from src.api.security import verify_telegram_init_data
from src.bot.database import BotDatabase, SUBSCRIPTION_PLANS
from src.security.rate_limiter import rate_limiter, BoundedTTLCache

router = APIRouter(prefix="/api", tags=["Auth & User"])

# Ultra-fast bounded in-memory cache for auth bootstrap bundles (max 2000 users, 45s TTL)
_AUTH_BUNDLE_CACHE = BoundedTTLCache[int, Dict[str, Any]](maxsize=2000, ttl_seconds=45.0)

def invalidate_auth_cache(user_id: int):
    _AUTH_BUNDLE_CACHE.pop(user_id, None)

class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., description="Raw initData string from Telegram WebApp")

class LanguageUpdateRequest(BaseModel):
    language: str = Field(..., pattern="^(uz_latn|uz_cyrl|ru)$")

class SubscriptionActivateRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID ('pro_14' or 'pro_30')")

@router.post("/auth/telegram")
def auth_telegram(req: TelegramAuthRequest, request: Request, db: BotDatabase = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"auth_ip:{client_ip}"
    allowed, _, retry_after = rate_limiter.is_allowed(rate_key, max_requests=30, window_seconds=60)
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

    return {
        "ok": True,
        **bundle
    }

@router.get("/user/me")
def get_user_me(user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    user_id = user["user_id"]
    stats = db.get_user_stats(user_id)
    streak = db.get_learning_streak(user_id)
    bookmarks = db.get_user_bookmarks(user_id)
    subscription = db.get_user_subscription(user_id)
    free_tier = db.get_user_free_tier_status(user_id)

    return {
        "user": user,
        "subscription": subscription,
        "free_tier": free_tier,
        "stats": stats,
        "streak": streak,
        "bookmarks_count": len(bookmarks),
        "history": db.get_exam_history(user_id, limit=5)
    }

@router.post("/user/language")
def set_language(req: LanguageUpdateRequest, user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    user_id = user["user_id"]
    db.set_user_language(user_id, req.language)
    return {"ok": True, "language": req.language}

# --- Subscription API Endpoints ---
@router.get("/subscription/plans")
def get_subscription_plans():
    return {
        "plans": list(SUBSCRIPTION_PLANS.values())
    }

@router.get("/subscription/status")
def get_subscription_status(user: Dict[str, Any] = Depends(get_current_user), db: BotDatabase = Depends(get_db)):
    sub = db.get_user_subscription(user["user_id"])
    ft = db.get_user_free_tier_status(user["user_id"])
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
