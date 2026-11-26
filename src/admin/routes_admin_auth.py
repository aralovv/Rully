"""
Admin Authentication Routes.
Handles:
- Username + Password verification
- Telegram OTP challenge creation and verification
- Session cookie management and logout
"""

import os
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from src.admin.auth_service import (
    initiate_admin_login,
    verify_admin_otp,
    revoke_admin_session
)
from src.admin.deps import get_current_admin
from src.security.rate_limiter import get_client_ip

router = APIRouter(prefix="/api/admin/auth", tags=["Admin Auth"])


class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")


class AdminOTPVerifyRequest(BaseModel):
    challenge_id: str = Field(..., description="Challenge ID received from login step")
    otp_code: str = Field(..., description="6-digit OTP code received on Telegram")


@router.post("/login")
async def admin_login(req: AdminLoginRequest, request: Request):
    """Step 1: Verifies username/password and sends OTP to Admin Telegram."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    success, message, data = await initiate_admin_login(
        username=req.username.strip(),
        password=req.password,
        ip_address=client_ip,
        user_agent=user_agent
    )

    if not success:
        raise HTTPException(status_code=401, detail=message)

    return {
        "ok": True,
        "message": message,
        "data": data
    }


@router.post("/otp/verify")
async def admin_otp_verify(req: AdminOTPVerifyRequest, request: Request, response: Response):
    """Step 2: Verifies single-use OTP and establishes authenticated session."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    success, message, data = await verify_admin_otp(
        challenge_id=req.challenge_id.strip(),
        otp_code=req.otp_code.strip(),
        ip_address=client_ip,
        user_agent=user_agent
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    session_token = data["session_token"]

    # Set secure HTTP-only cookie with environment-aware Secure flag
    is_secure = bool(
        os.getenv("VERCEL")
        or os.getenv("RENDER")
        or os.getenv("ENVIRONMENT", "").lower() in ["production", "prod"]
        or request.url.scheme == "https"
    )

    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=12 * 3600,
        path="/"
    )

    return {
        "ok": True,
        "message": message,
        "data": {
            "admin": data["admin"],
            "session_token": session_token,
            "expires_at": data["expires_at"]
        }
    }


@router.post("/logout")
async def admin_logout(response: Response, current_admin: dict = Depends(get_current_admin)):
    """Logs out and revokes the active session token."""
    session_id = current_admin.get("session_id")
    if session_id:
        revoke_admin_session(session_id)

    response.delete_cookie(key="admin_session", path="/")
    return {"ok": True, "message": "Muvaffaqiyatli chiqildi"}


@router.get("/me")
async def admin_me(current_admin: dict = Depends(get_current_admin)):
    """Returns the current logged-in administrator profile."""
    return {
        "ok": True,
        "admin": {
            "id": current_admin["id"],
            "username": current_admin["username"],
            "telegram_id": current_admin["telegram_id"],
            "role": current_admin["role"]
        }
    }
