"""
FastAPI Dependencies for Admin Control Panel.
Enforces admin authentication and extracts session context.
"""

from fastapi import Request, HTTPException, Depends, Header, Cookie
from typing import Optional, Dict, Any
from src.admin.auth_service import validate_admin_session


async def get_current_admin(
    request: Request,
    admin_session: Optional[str] = Cookie(None, alias="admin_session"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_admin_session: Optional[str] = Header(None, alias="X-Admin-Session")
) -> Dict[str, Any]:
    """
    Extracts and validates admin session from:
    1. HTTP-only secure Cookie ('admin_session')
    2. Header 'X-Admin-Session'
    3. Header 'Authorization: Bearer <token>'
    """
    token = None
    if admin_session:
        token = admin_session
    elif x_admin_session:
        token = x_admin_session
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="ADMIN_UNAUTHORIZED: Missing administrative session token"
        )

    admin = validate_admin_session(token)
    if not admin:
        raise HTTPException(
            status_code=401,
            detail="ADMIN_SESSION_INVALID: Session expired, revoked, or invalid"
        )

    return admin
