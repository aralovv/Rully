"""
RULLY Avtotest Telegram Mini App & Admin Financial Control Center - FastAPI Main Application.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

# User-facing Mini App Routers
from src.api.routes_auth import router as auth_router
from src.api.routes_theory import router as theory_router
from src.api.routes_practical import router as practical_router
from src.api.routes_payment import router as payment_router
from src.api.routes_telegram import router as telegram_router
from src.api.routes_ai import router as ai_router

# Admin Control Panel Routers
from src.admin.routes_admin_auth import router as admin_auth_router
from src.admin.routes_admin_dashboard import router as admin_dashboard_router
from src.admin.routes_admin_users import router as admin_users_router
from src.admin.routes_admin_plans import router as admin_plans_router
from src.admin.routes_admin_cards import router as admin_cards_router
from src.admin.routes_admin_orders import router as admin_orders_router
from src.admin.routes_admin_payments import router as admin_payments_router
from src.admin.routes_admin_mtproto import router as admin_mtproto_router
from src.admin.routes_admin_analytics import router as admin_analytics_router
from src.admin.routes_admin_logs import router as admin_logs_router
from src.admin.routes_admin_broadcast import router as admin_broadcast_router
from src.admin.routes_admin_questions import router as admin_questions_router

# System & Lifecycle Services
from src.database_migrations import run_migrations
from src.admin.auth_service import ensure_admin_user_exists
from src.mtproto.service import get_mtproto_manager
from src.payments.order_manager import expire_stale_orders

logger = logging.getLogger(__name__)

# Background worker for order expiration
async def order_expiration_worker():
    """Runs every 60 seconds to expire stale payment orders."""
    while True:
        try:
            expired_count = expire_stale_orders()
            if expired_count > 0:
                logger.info(f"Order expiration worker: Expired {expired_count} stale orders.")
        except Exception as e:
            logger.error(f"Error in order expiration worker: {e}")
        await asyncio.sleep(60)


async def periodic_question_sync_worker():
    """Periodically checks external theory sources for new questions every 12 hours."""
    await asyncio.sleep(60)  # Initial grace delay after startup
    while True:
        try:
            from src.sync.service import QuestionSyncService
            svc = QuestionSyncService()
            check_res = svc.check_for_updates(auto_stage=True)
            if check_res.get("has_updates"):
                logger.info(f"Periodic question sync worker: Staged {check_res.get('newly_staged_count', 0)} items for admin review.")
        except Exception as e:
            logger.error(f"Error in periodic question sync worker: {e}")
        await asyncio.sleep(43200)  # 12 hours


IS_VERCEL = bool(os.getenv("VERCEL"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Run migrations and database schema updates only on local development
    if not IS_VERCEL:
        try:
            run_migrations()
            ensure_admin_user_exists()
        except Exception as e:
            logger.error(f"Startup migration error: {e}")

    expiration_task = None
    question_sync_task = None

    if not IS_VERCEL:
        # 2. Start background order expiration task
        expiration_task = asyncio.create_task(order_expiration_worker())

        # 3. Start periodic question sync worker
        question_sync_task = asyncio.create_task(periodic_question_sync_worker())

        # 4. Attempt to initialize MTProto client if stored session exists
        try:
            mtproto = get_mtproto_manager()
            asyncio.create_task(mtproto.initialize_and_start())
        except Exception as e:
            logger.error(f"MTProto startup initialization error: {e}")
    else:
        logger.info("Running in Vercel Serverless environment. Long-running daemons disabled.")

    yield

    # Teardown
    if expiration_task:
        expiration_task.cancel()
    if question_sync_task:
        question_sync_task.cancel()
    if not IS_VERCEL:
        try:
            await get_mtproto_manager().disconnect()
        except Exception:
            pass


app = FastAPI(
    title="RULLY Avtotest & Admin Financial Gateway API",
    description="REST API for RULLY Telegram Mini App & Admin MTProto Payment Control Center",
    version="2.1.0",
    lifespan=lifespan
)

# CORS Configuration for Mini App webviews and private admin web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static") or path in ("/", "/index.html", "/admin", "/admin/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include User Mini App API Routers
app.include_router(auth_router)
app.include_router(theory_router)
app.include_router(practical_router)
app.include_router(payment_router)
app.include_router(telegram_router)
app.include_router(ai_router)

# Include Admin Control Panel Routers
app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_users_router)
app.include_router(admin_plans_router)
app.include_router(admin_cards_router)
app.include_router(admin_orders_router)
app.include_router(admin_payments_router)
app.include_router(admin_mtproto_router)
app.include_router(admin_analytics_router)
app.include_router(admin_logs_router)
app.include_router(admin_broadcast_router)
app.include_router(admin_questions_router)

# Serve & Proxy Images with Local + Remote Fallback & Edge Caching
images_dir = os.path.abspath("data/images/original")

@app.get("/images/{filename}")
async def serve_image(filename: str):
    """
    High-resiliency image delivery endpoint:
    1. Returns local file if present on disk with immutable caching.
    2. In serverless environments (e.g. Vercel), proxies from GitHub Raw with 1-year immutable edge caching.
    """
    clean_name = os.path.basename(filename.replace("\\", "/"))
    local_path = os.path.join(images_dir, clean_name)
    if os.path.exists(local_path):
        return FileResponse(
            local_path,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=31536000, immutable"}
        )

    # Serverless fallback: Proxy from GitHub Raw with edge caching
    gh_raw_url = f"https://raw.githubusercontent.com/aralovv/Rully/main/data/images/original/{clean_name}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(gh_raw_url)
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type="image/webp",
                    headers={
                        "Cache-Control": "public, max-age=31536000, s-maxage=31536000, immutable",
                        "X-Proxy-Source": "github-raw"
                    }
                )
    except Exception as e:
        logger.warning(f"Failed to fetch image {clean_name} from GitHub Raw: {e}")

    return Response(status_code=404, content="Image not found")

# Mount Static Assets
static_dir = os.path.abspath("static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "rully-miniapp-api",
        "version": "2.0.0",
        "canonical_db": "master_database.sqlite"
    }

# --- Independent Admin Panel Route ---
@app.get("/admin")
@app.get("/admin/")
async def serve_admin_panel():
    admin_index = os.path.join(static_dir, "admin", "index.html")
    if os.path.exists(admin_index):
        return FileResponse(admin_index)
    return {"error": "Admin panel template not found"}

# --- User Mini App Route ---
@app.get("/")
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "RULLY Mini App API is running."}
