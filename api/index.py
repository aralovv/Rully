"""
Vercel Serverless Entrypoint for RULLY Avtotest API.
"""

import sys
import os
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Top-level ASGI app for Vercel AST analysis
app = FastAPI(title="RULLY Production Gateway")

import_error = None
try:
    from src.api.main import app as main_app
    app.mount("/", main_app)
except Exception as e:
    import_error = traceback.format_exc()

@app.get("/api/health-check")
async def health_check_direct():
    return {
        "status": "healthy",
        "service": "rully-vercel",
        "has_turso_url": bool(os.getenv("TURSO_DATABASE_URL")),
        "has_turso_token": bool(os.getenv("TURSO_AUTH_TOKEN")),
        "import_error": import_error
    }
