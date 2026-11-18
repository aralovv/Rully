"""
User Payment Order API Routes for Telegram Mini App & Bot.
Provides:
- Automated order creation with unique suffix allocation (1..999 UZS)
- Active invoice polling to automatically unlock PRO upon MTProto verification
- Strict prohibition of manual payment confirmation buttons
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from src.api.deps import get_current_user
from src.payments.order_manager import (
    create_or_get_payment_order,
    get_user_active_order,
    get_order_by_id
)
from src.security.telegram_notifier import send_payment_invoice_to_user, send_order_created_alert

router = APIRouter(prefix="/api/payment", tags=["User Payment"])


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
    """
    user_id = user["user_id"]
    success, message, order = create_or_get_payment_order(user_id, req.plan_id.strip())
    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Deliver in-bot payment details notification
    try:
        raw_card = order.get("card_number_raw") or order.get("card_number_masked", "")
        asyncio.create_task(send_payment_invoice_to_user(
            user_id=user_id,
            plan_name=order.get("plan_name") or ("30 kunlik PRO" if "30" in req.plan_id else "14 kunlik PRO"),
            cardholder_name=order.get("cardholder_name", "ANVARJON ARALOV"),
            card_number_full=raw_card,
            final_amount_uzs=order.get("final_amount_uzs", 0),
            order_id=order.get("order_id", "")
        ))
        if message == "Yangi to‘lov buyurtmasi yaratildi.":
            asyncio.create_task(send_order_created_alert(order))
    except Exception:
        pass

    return {
        "ok": True,
        "message": message,
        "order": order
    }


@router.get("/orders/active")
async def api_get_active_order(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves user's currently active pending order, if any."""
    order = get_user_active_order(user["user_id"])
    return {
        "ok": True,
        "has_active_order": order is not None,
        "order": order
    }


@router.get("/orders/{order_id}/status")
async def api_get_order_status(
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
