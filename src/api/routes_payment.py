"""
User Payment Order API Routes for Telegram Mini App & Bot.
Provides:
- Automated order creation with unique suffix allocation (1..999 UZS)
- Active invoice polling to automatically unlock PRO upon MTProto verification
- Strict prohibition of manual payment confirmation buttons
"""

import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from src.api.deps import get_current_user
from src.security.rate_limiter import rate_limiter, BoundedTTLCache
from src.payments.order_manager import (
    create_or_get_payment_order,
    get_user_active_order,
    get_order_by_id
)
from src.payments.stars_service import (
    create_stars_invoice_order,
    get_stars_order_status,
)
from src.security.telegram_notifier import send_payment_invoice_to_user, send_order_created_alert

router = APIRouter(prefix="/api/payment", tags=["User Payment"])

# Bounded per-user debounce lock (2.5s TTL, max 2000 users) to eliminate rapid double-clicks
_user_order_locks = BoundedTTLCache[int, float](maxsize=2000, ttl_seconds=2.5)


class CreateOrderRequest(BaseModel):
    plan_id: str = Field(..., description="Plan ID ('pro_14' or 'pro_30')")


@router.post("/orders/create")
async def api_create_payment_order(
    req: CreateOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates an automated payment order with unique payment suffix.
    If an unexpired order already exists for the same plan, reopens that exact order.
    Also sends payment invoice directly to user in Telegram bot chat.
    Includes atomic debounce protection against rapid button double-clicks.
    """
    user_id = user["user_id"]

    # Rate limiting (P0): max 3 order creation requests per minute per user
    allowed, _, retry_after = rate_limiter.is_allowed(f"order_create:{user_id}", max_requests=3, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many order creation requests. Please wait {int(retry_after)}s before creating a new order."
        )

    if _user_order_locks.get(user_id):
        # Rapid double-click within 2.5 seconds:
        # Idempotently return the user's active pending order without blocking event loop
        existing = await asyncio.to_thread(get_user_active_order, user_id)
        if existing:
            return {
                "ok": True,
                "message": "Amaldagi to‘lov buyurtmasi ochildi.",
                "order": existing
            }

    _user_order_locks.set(user_id, time.time())
    success, message, order = await asyncio.to_thread(create_or_get_payment_order, user_id, req.plan_id.strip())
    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Deliver in-bot payment details notification (awaited cleanly so serverless requests do not cancel tasks)
    try:
        raw_card = order.get("card_number_raw") or order.get("card_number_masked", "")
        notify_coros = [
            send_payment_invoice_to_user(
                user_id=user_id,
                plan_name=order.get("plan_name") or ("30 kunlik PRO" if "30" in req.plan_id else "14 kunlik PRO"),
                cardholder_name=order.get("cardholder_name", "ANVARJON ARALOV"),
                card_number_full=raw_card,
                final_amount_uzs=order.get("final_amount_uzs", 0),
                order_id=order.get("order_id", ""),
            )
        ]
        if "yaratildi" in (message or "").lower():
            notify_coros.append(send_order_created_alert(order))
        await asyncio.gather(*notify_coros, return_exceptions=True)
    except Exception:
        pass

    return {
        "ok": True,
        "message": message,
        "order": order
    }


@router.get("/orders/active")
def api_get_active_order(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves user's currently active pending order, if any."""
    order = get_user_active_order(user["user_id"])
    return {
        "ok": True,
        "has_active_order": order is not None,
        "order": order
    }


@router.get("/orders/{order_id}/status")
def api_get_order_status(
    order_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Polls the status of a specific order.
    Used by the invoice countdown screen to detect when MTProto verifies the transfer.
    """
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: Order belongs to another user")

    return {
        "ok": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "is_paid": order["status"] == "PAID",
        "is_expired": order["status"] == "EXPIRED",
        "remaining_seconds": order.get("remaining_seconds", 0),
        "paid_at": order.get("paid_at")
    }


@router.post("/stars/invoice")
async def api_create_stars_invoice(
    req: CreateOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Creates a native Telegram Stars (`XTR`) invoice link via Bot API (`createInvoiceLink`)
    for direct checkout in Telegram Mini App (`WebApp.openInvoice`) or web-to-Telegram redirect.
    """
    user_id = user["user_id"]
    allowed, _, retry_after = rate_limiter.is_allowed(f"stars_invoice:{user_id}", max_requests=5, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many Stars invoice requests. Please wait {int(retry_after)}s.",
        )

    try:
        res = await create_stars_invoice_order(user_id=user_id, plan_id=req.plan_id.strip(), create_link=True)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/stars/{order_id}/status")
async def api_get_stars_order_status(
    order_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Polls Telegram Stars (`XTR`) invoice fulfillment status."""
    status_code, payload = await asyncio.to_thread(get_stars_order_status, order_id, user["user_id"])
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=payload.get("detail", "Stars order error"))
    return payload
