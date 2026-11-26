"""
FastAPI Dependencies for Admin Control Panel.
Enforces admin authentication and extracts session context.
"""

import secrets
from urllib.parse import urlparse
from fastapi import Request, HTTPException, Depends, Header, Cookie
from typing import Optional, Dict, Any
from src.admin.auth_service import validate_admin_session


def _verify_cookie_csrf(request: Request, rully_csrf: Optional[str], x_csrf_token: Optional[str]):
    """Enforces double-submit CSRF cookie + header + same-origin verification for cookie-authenticated mutations."""
    origin = request.headers.get("origin")
    host_header = request.headers.get("host")
    if origin and host_header:
        parsed_origin = urlparse(origin)
        if parsed_origin.netloc and parsed_origin.netloc.lower() != host_header.lower():
            raise HTTPException(status_code=403, detail="CSRF_ORIGIN_MISMATCH")

    if not rully_csrf or not x_csrf_token or not secrets.compare_digest(rully_csrf, x_csrf_token):
        raise HTTPException(
            status_code=403,
            detail="CSRF_TOKEN_INVALID: Missing or mismatched X-CSRF-Token header"
        )


async def get_current_admin(
    request: Request,
    admin_session: Optional[str] = Cookie(None, alias="admin_session"),
    rully_csrf: Optional[str] = Cookie(None, alias="rully_csrf"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_admin_session: Optional[str] = Header(None, alias="X-Admin-Session"),
    x_csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
) -> Dict[str, Any]:
    """
    Extracts and validates admin session from:
    1. HTTP-only secure Cookie ('admin_session') + double-submit CSRF protection on mutations
    2. Header 'X-Admin-Session'
    3. Header 'Authorization: Bearer <token>'
    """
    token = None
    using_cookie = False
    if x_admin_session:
        token = x_admin_session
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif admin_session:
        token = admin_session
        using_cookie = True

    if not token:
        raise HTTPException(
            status_code=401,
            detail="ADMIN_UNAUTHORIZED: Missing administrative session token"
        )

    if using_cookie and request.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        _verify_cookie_csrf(request, rully_csrf, x_csrf_token)

    admin = validate_admin_session(token)
    if not admin:
        raise HTTPException(
            status_code=401,
            detail="ADMIN_SESSION_INVALID: Session expired, revoked, or invalid"
        )

    return admin


def require_admin_role(*allowed_roles: str):
    """Role-Based Access Control (RBAC) dependency factory. SUPERADMIN always holds global authority."""
    normalized = {r.strip().upper() for r in allowed_roles if r.strip()} | {"SUPERADMIN"}

    async def _role_guard(current_admin: Dict[str, Any] = Depends(get_current_admin)) -> Dict[str, Any]:
        role = str(current_admin.get("role") or "").strip().upper()
        if role not in normalized:
            raise HTTPException(
                status_code=403,
                detail=f"ADMIN_ROLE_FORBIDDEN: Role '{role or 'UNKNOWN'}' lacks permission for this action"
            )
        return current_admin

    return _role_guard
