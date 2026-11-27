"""
Admin Payment Card Management Routes.
Supports:
- Adding, editing, disabling, and enabling receiving bank cards
- Encryption of full card numbers at rest using AES-CBC/Fernet
- Card masking in all views (e.g. '9860 **** **** 5370')
- Association with MTProto monitoring
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin, require_admin_role
from src.db_adapter import execute_batch, get_db_connection
from src.payments.order_manager import invalidate_payment_cache
from src.security.crypto import encrypt_data, mask_card_number

router = APIRouter(
    prefix="/api/admin/cards",
    tags=["Admin Payment Cards"],
    dependencies=[Depends(require_admin_role("FINANCE"))],
)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")

def _get_connection():
    return get_db_connection(DB_PATH)


class CardCreateRequest(BaseModel):
    cardholder_name: str = Field(..., description="Cardholder full name (e.g. ANVARJON ARALOV)")
    card_number: str = Field(..., description="Full 16-digit card number")
    card_type: str = Field("HUMO", description="HUMO or UZCARD")
    display_name: str = Field(..., description="Display title for card")
    is_monitoring: bool = Field(True, description="Whether MTProto actively monitors this card")


class CardUpdateRequest(BaseModel):
    cardholder_name: Optional[str] = None
    card_number: Optional[str] = None
    card_type: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_monitoring: Optional[bool] = None


class ActivateCardRequest(BaseModel):
    make_exclusive: bool = True
    is_monitoring: bool = True


_ALLOWED_CARD_TYPES = {"HUMO", "UZCARD", "VISA", "MASTERCARD"}


def _clean_and_validate_card_number(raw: str) -> str:
    clean_num = (raw or "").strip().replace(" ", "").replace("-", "")
    if len(clean_num) != 16 or not clean_num.isdigit():
        raise HTTPException(status_code=400, detail="Karta raqami aniq 16 xonali raqam bo‘lishi shart.")
    return clean_num


def _normalize_card_type(raw: Optional[str]) -> str:
    c_type = (raw or "HUMO").strip().upper()
    if c_type not in _ALLOWED_CARD_TYPES:
        raise HTTPException(status_code=400, detail=f"Noto‘g‘ri karta turi: {c_type}")
    return c_type


@router.get("")
def list_payment_cards(current_admin: dict = Depends(get_current_admin)):
    """Lists payment cards with masked numbers (never exposing unencrypted card numbers)."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, id AS card_id, cardholder_name, card_number_masked, card_suffix,
                   card_type, display_name, is_active, is_monitoring, created_at, updated_at
            FROM payment_cards
            ORDER BY is_active DESC, is_monitoring DESC, id ASC
        """)
        cards = [dict(r) for r in c.fetchall()]
    return {"ok": True, "cards": cards}


@router.post("")
def create_payment_card(req: CardCreateRequest, current_admin: dict = Depends(get_current_admin)):
    """Adds a new payment card, encrypting full number and extracting 4-digit suffix."""
    clean_num = _clean_and_validate_card_number(req.card_number)
    card_type = _normalize_card_type(req.card_type)
    masked, suffix = mask_card_number(clean_num)
    encrypted_number = encrypt_data(clean_num)
    now_str = datetime.utcnow().isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO payment_cards (
                cardholder_name, card_number_encrypted, card_number_masked, card_suffix,
                card_type, display_name, is_active, is_monitoring, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """, (
            req.cardholder_name.strip().upper(),
            encrypted_number,
            masked,
            suffix,
            card_type,
            req.display_name.strip(),
            1 if req.is_monitoring else 0,
            now_str,
            now_str
        ))
        card_id = c.lastrowid

        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'PAYMENT_CARD_ADDED', ?, ?)
        """, (current_admin["id"], f"Card ID: {card_id}, Masked: {masked}, Suffix: {suffix}", now_str))

        conn.commit()
    invalidate_payment_cache()

    return {"ok": True, "message": "Yangi bank kartasi muvaffaqiyatli saqlandi.", "card_id": card_id}


@router.put("/active")
@router.put("/{card_id}")
def update_payment_card(
    card_id: Optional[str] = "active",
    req: CardUpdateRequest = None,
    current_admin: dict = Depends(get_current_admin)
):
    """Updates card metadata, active toggle, or MTProto monitoring status."""
    if req is None:
        req = CardUpdateRequest()

    explicit_id_requested = bool(card_id and card_id not in ("active", "undefined"))
    target_id: Optional[int] = None
    if explicit_id_requested:
        try:
            target_id = int(card_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Noto‘g‘ri karta ID formati")

    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        card = None
        if target_id is not None:
            c.execute("SELECT * FROM payment_cards WHERE id = ?", (target_id,))
            card = c.fetchone()
            if not card and explicit_id_requested:
                raise HTTPException(status_code=404, detail="Karta topilmadi")

        if not card and not explicit_id_requested:
            c.execute("SELECT * FROM payment_cards ORDER BY is_active DESC, is_monitoring DESC, id ASC LIMIT 1")
            card = c.fetchone()
            if card:
                target_id = card["id"]

        if not card:
            clean_num = _clean_and_validate_card_number(req.card_number or "9860000000005370")
            masked, suffix = mask_card_number(clean_num)
            encrypted_number = encrypt_data(clean_num)
            holder = (req.cardholder_name or "ANVARJON ARALOV").strip().upper()
            c_type = _normalize_card_type(req.card_type)
            c.execute("""
                INSERT INTO payment_cards (
                    cardholder_name, card_number_encrypted, card_number_masked, card_suffix,
                    card_type, display_name, is_active, is_monitoring, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'Asosiy karta', 1, 1, ?, ?)
            """, (holder, encrypted_number, masked, suffix, c_type, now_str, now_str))
            target_id = c.lastrowid
            conn.commit()
            invalidate_payment_cache()
            return {"ok": True, "message": "Yangi bank kartasi saqlandi.", "card_id": target_id}

        updates = []
        params = []
        if req.card_number is not None and req.card_number.strip():
            clean_num = _clean_and_validate_card_number(req.card_number)
            masked, suffix = mask_card_number(clean_num)
            encrypted_num = encrypt_data(clean_num)
            updates.append("card_number_encrypted = ?")
            params.append(encrypted_num)
            updates.append("card_number_masked = ?")
            params.append(masked)
            updates.append("card_suffix = ?")
            params.append(suffix)

        if req.cardholder_name is not None and req.cardholder_name.strip():
            updates.append("cardholder_name = ?")
            params.append(req.cardholder_name.strip().upper())
        if req.card_type is not None and req.card_type.strip():
            updates.append("card_type = ?")
            params.append(_normalize_card_type(req.card_type))
        if req.display_name is not None and req.display_name.strip():
            updates.append("display_name = ?")
            params.append(req.display_name.strip())
        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if req.is_active else 0)
        if req.is_monitoring is not None:
            updates.append("is_monitoring = ?")
            params.append(1 if req.is_monitoring else 0)

        if updates:
            updates.append("updated_at = ?")
            params.append(now_str)
            params.append(target_id)
            execute_batch(conn, [
                (f"UPDATE payment_cards SET {', '.join(updates)} WHERE id = ?", params),
                (
                    """
                    INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                    VALUES (?, 'PAYMENT_CARD_UPDATED', ?, ?)
                    """,
                    [current_admin["id"], f"Card ID: {target_id}", now_str],
                ),
            ])
            invalidate_payment_cache()

    return {"ok": True, "message": "Karta ma’lumotlari muvaffaqiyatli saqlandi.", "card_id": target_id}


@router.post("/{card_id}/activate")
def activate_payment_card(
    card_id: int,
    req: Optional[ActivateCardRequest] = None,
    current_admin: dict = Depends(get_current_admin),
):
    """Activates a card and optionally designates it as the primary MTProto-monitored receiving card."""
    opts = req or ActivateCardRequest()
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, card_number_masked FROM payment_cards WHERE id = ?", (card_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Karta topilmadi")

        stmts: List[Any] = []
        if opts.make_exclusive and opts.is_monitoring:
            stmts.append((
                "UPDATE payment_cards SET is_monitoring = 0, updated_at = ? WHERE id != ?",
                [now_str, card_id],
            ))
        stmts.append((
            "UPDATE payment_cards SET is_active = 1, is_monitoring = ?, updated_at = ? WHERE id = ?",
            [1 if opts.is_monitoring else 0, now_str, card_id],
        ))
        stmts.append((
            """
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'PAYMENT_CARD_ACTIVATED', ?, ?)
            """,
            [current_admin["id"], f"Card ID: {card_id}, Exclusive: {opts.make_exclusive}", now_str],
        ))
        execute_batch(conn, stmts)
    invalidate_payment_cache()
    return {"ok": True, "message": "Karta asosiy qabul qiluvchi sifatida faollashtirildi.", "card_id": card_id}


@router.delete("/{card_id}")
def disable_payment_card(card_id: int, current_admin: dict = Depends(get_current_admin)):
    """Deactivates a card atomically (preserving historical references)."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM payment_cards WHERE id = ?", (card_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Card not found")

        execute_batch(conn, [
            (
                "UPDATE payment_cards SET is_active = 0, is_monitoring = 0, updated_at = ? WHERE id = ?",
                [now_str, card_id],
            ),
            (
                """
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (?, 'PAYMENT_CARD_DISABLED', ?, ?)
                """,
                [current_admin["id"], f"Card ID: {card_id}", now_str],
            ),
        ])
    invalidate_payment_cache()

    return {"ok": True, "message": "Karta muvaffaqiyatli o‘chirildi (nofaol qilindi)."}
