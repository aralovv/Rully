"""
Admin Subscription Plan Management Routes.
Supports:
- Dynamic plan configuration
- Safe price modifications applying exclusively to newly created orders
- Immutable price change audit trail
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin

router = APIRouter(prefix="/api/admin/plans", tags=["Admin Plans"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class UpdatePriceRequest(BaseModel):
    new_price_uzs: int = Field(..., ge=1000, description="New base price in UZS")
    reason: str = Field(..., description="Administrative reason for changing the price")


class PlanCreateRequest(BaseModel):
    id: str = Field(..., description="Unique plan identifier, e.g. pro_60")
    name: str = Field(..., description="Plan display name")
    duration_days: int = Field(..., ge=1, description="Duration in days")
    base_price_uzs: int = Field(..., ge=1000, description="Base price in UZS")
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


@router.get("")
async def list_subscription_plans(current_admin: dict = Depends(get_current_admin)):
    """Returns all subscription plans from the database."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM subscription_plans ORDER BY display_order ASC, id ASC")
        plans = [dict(r) for r in c.fetchall()]
    return {"ok": True, "plans": plans}


@router.post("")
async def create_subscription_plan(req: PlanCreateRequest, current_admin: dict = Depends(get_current_admin)):
    """Creates a new subscription plan."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO subscription_plans (
                    id, name, duration_days, base_price_uzs, description, is_active, display_order, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.id.strip().lower(), req.name.strip(), req.duration_days,
                req.base_price_uzs, req.description, 1 if req.is_active else 0,
                req.display_order, now_str, now_str
            ))
            c.execute("""
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (?, 'SUBSCRIPTION_PLAN_CREATED', ?, ?)
            """, (current_admin["id"], f"Plan: {req.id}, Name: {req.name}, Price: {req.base_price_uzs} UZS", now_str))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Plan ID already exists")

    return {"ok": True, "message": "Yangi tarif muvaffaqiyatli yaratildi."}


@router.put("/{plan_id}")
async def update_subscription_plan(
    plan_id: str,
    req: PlanUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Updates non-monetary plan details (name, description, active status)."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,))
        plan = c.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        updates = []
        params = []
        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name.strip())
        if req.description is not None:
            updates.append("description = ?")
            params.append(req.description.strip())
        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if req.is_active else 0)
        if req.display_order is not None:
            updates.append("display_order = ?")
            params.append(req.display_order)

        if updates:
            updates.append("updated_at = ?")
            params.append(now_str)
            params.append(plan_id)
            c.execute(f"UPDATE subscription_plans SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

    return {"ok": True, "message": "Tarif ma’lumotlari yangilandi."}


@router.post("/{plan_id}/price")
async def update_plan_price(
    plan_id: str,
    req: UpdatePriceRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Modifies subscription plan price.
    CRITICAL: Applies exclusively to new orders; preserves existing order snapshots.
    Records change history in subscription_price_history.
    """
    now_str = datetime.utcnow().isoformat()
    admin_name = current_admin["username"]

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,))
        plan = c.fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        old_price = plan["base_price_uzs"]
        new_price = req.new_price_uzs

        # 1. Update base price
        c.execute("""
            UPDATE subscription_plans 
            SET base_price_uzs = ?, updated_at = ?
            WHERE id = ?
        """, (new_price, now_str, plan_id))

        # 2. Record immutable price history
        c.execute("""
            INSERT INTO subscription_price_history (
                plan_id, old_price_uzs, new_price_uzs, changed_by_admin, reason, changed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (plan_id, old_price, new_price, admin_name, req.reason.strip(), now_str))

        # 3. Log audit event
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'PLAN_PRICE_CHANGED', ?, ?)
        """, (current_admin["id"], f"Plan: {plan_id}, Old: {old_price} UZS, New: {new_price} UZS, Reason: {req.reason}", now_str))

        conn.commit()

    return {
        "ok": True,
        "message": f"Tarif narxi muvaffaqiyatli o‘zgartirildi: {old_price:,} -> {new_price:,} UZS".replace(",", " ")
    }


@router.get("/{plan_id}/price-history")
async def get_price_history(plan_id: str, current_admin: dict = Depends(get_current_admin)):
    """Returns the immutable price change audit log for a plan."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM subscription_price_history 
            WHERE plan_id = ? 
            ORDER BY changed_at DESC
        """, (plan_id,))
        history = [dict(r) for r in c.fetchall()]
    return {"ok": True, "history": history}
