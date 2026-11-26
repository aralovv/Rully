"""
Vercel Serverless Entrypoint for RULLY Avtotest API.
Uses public-only router split (lazy-loading admin routes only when needed) for fast cold starts.
"""

import logging
import os
import sys
import time
import traceback
from fastapi import FastAPI

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger("rully.vercel")

# Top-level ASGI app for Vercel AST analysis
app = FastAPI(title="RULLY Production Gateway")

import_error = None
_mount_ms = 0.0


@app.get("/api/health-check")
async def health_check_direct():
    return {
        "status": "healthy" if import_error is None else "degraded",
        "service": "rully-vercel",
        "mount_ms": _mount_ms,
        "import_ok": import_error is None,
        "has_turso_url": bool(os.getenv("TURSO_DATABASE_URL")),
        "has_turso_token": bool(os.getenv("TURSO_AUTH_TOKEN")),
    }


_t0 = time.perf_counter()
try:
    from src.api.main import app as main_app
    app.mount("/", main_app)
except Exception:
    import_error = traceback.format_exc()
    logger.exception("Failed to mount main ASGI application")
_mount_ms = round((time.perf_counter() - _t0) * 1000.0, 2)
