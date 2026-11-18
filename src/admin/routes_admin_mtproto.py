"""
Admin MTProto Integration & Payment Detection Controller.
Supports:
- Monitoring connection health and Humocardbot availability
- Web-driven interactive Telegram connection (Phone -> Code -> 2FA)
- Session disconnection
- Real-time Humocard notification test simulation
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.admin.deps import get_current_admin
from src.mtproto.service import get_mtproto_manager

router = APIRouter(prefix="/api/admin/mtproto", tags=["Admin MTProto Integration"])
logger = logging.getLogger(__name__)


class PhoneRequest(BaseModel):
    phone_number: str = Field(..., description="Telegram phone number in international format, e.g. +998901234567")
    api_id: Optional[int] = Field(None, description="Optional custom Telegram API ID")
    api_hash: Optional[str] = Field(None, description="Optional custom Telegram API Hash")


class CodeRequest(BaseModel):
    code: str = Field(..., description="Verification code received from Telegram")


class Password2FARequest(BaseModel):
    password: str = Field(..., description="Telegram Two-Step Verification (2FA) password")


class SimulateNotificationRequest(BaseModel):
    raw_message: str = Field(..., description="Raw text of Humocardbot notification message")


@router.get("/status")
async def get_mtproto_status(current_admin: dict = Depends(get_current_admin)):
    """Returns MTProto connection health, monitored bot status, and telemetry."""
    manager = get_mtproto_manager()
    status = manager.get_status()
    return {"ok": True, "status": status}


@router.post("/send-code")
async def request_mtproto_code(req: PhoneRequest, current_admin: dict = Depends(get_current_admin)):
    """Initiates MTProto connection by requesting a Telegram authentication code."""
    manager = get_mtproto_manager()
    success, message = await manager.request_phone_code(req.phone_number, req.api_id, req.api_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@router.post("/sign-in")
async def submit_mtproto_code(req: CodeRequest, current_admin: dict = Depends(get_current_admin)):
    """Submits the Telegram verification code."""
    manager = get_mtproto_manager()
    success, message, requires_2fa = await manager.submit_phone_code(req.code)
    if requires_2fa:
        return {"ok": False, "requires_2fa": True, "message": message}
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@router.post("/sign-in-2fa")
async def submit_mtproto_2fa(req: Password2FARequest, current_admin: dict = Depends(get_current_admin)):
    """Submits the Two-Step Verification password if enabled on the Telegram account."""
    manager = get_mtproto_manager()
    success, message = await manager.submit_2fa_password(req.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@router.post("/disconnect")
async def disconnect_mtproto(current_admin: dict = Depends(get_current_admin)):
    """Disconnects the active MTProto session and removes stored credentials."""
    manager = get_mtproto_manager()
    success, message = await manager.disconnect()
    return {"ok": success, "message": message}


@router.post("/simulate-notification")
async def simulate_humocard_notification(
    req: SimulateNotificationRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Simulates a Humocardbot notification through the payment parser and matching engine.
    Indispensable for automated testing, end-to-end audit, and administrator testing.
    """
    manager = get_mtproto_manager()
    result = await manager.simulate_notification(req.raw_message)
    return result
