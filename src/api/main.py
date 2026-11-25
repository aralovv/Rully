"""
RULLY Avtotest Telegram Mini App & Admin Financial Control Center - FastAPI Main Application.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
from src.payments.order_manager import expire_stale_orders

logger = logging.getLogger(__name__)

# Background worker for order expiration
async def order_expiration_worker():
    """Runs periodically (every 15 minutes) to expire stale payment orders without waking up CPU constantly."""
    while True:
        try:
            expired_count = expire_stale_orders()
            if expired_count > 0:
                logger.info(f"Order expiration worker: Expired {expired_count} stale orders.")
        except Exception as e:
            logger.error(f"Error in order expiration worker: {e}")
        await asyncio.sleep(900)


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
_bot_instance = None
_dp_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_instance, _dp_instance

    # 1. Run migrations and database schema updates only on local development
    if not IS_VERCEL:
        try:
            run_migrations()
            ensure_admin_user_exists()
        except Exception as e:
            logger.error(f"Startup migration error: {e}")

    expiration_task = None
    question_sync_task = None
    mtproto_task = None
    bot_task = None

    if not IS_VERCEL:
        # 2. Start background order expiration task
        expiration_task = asyncio.create_task(order_expiration_worker())

        # 3. Start periodic question sync worker
        question_sync_task = asyncio.create_task(periodic_question_sync_worker())

        # 4. Start resilient 24/7 MTProto worker loop
        async def mtproto_worker_loop():
            from src.mtproto.service import get_mtproto_manager
            from src.security.telegram_notifier import send_mtproto_status_alert
            manager = get_mtproto_manager()
            retry_delay = 5
            while True:
                try:
                    logger.info("Initializing and connecting MTProto client from stored session...")
                    connected = await manager.initialize_and_start()
                    if not connected:
                        if manager.connection_status == "NOT_INSTALLED":
                            logger.error(
                                "MTProto cannot start because Telethon is not installed. "
                                "Ensure Render Build Command uses requirements-render.txt."
                            )
                            await send_mtproto_status_alert(
                                "NOT_INSTALLED",
                                "Render muhitida Telethon kutubxonasi topilmadi (Build Commandni tekshiring)."
                            )
                            await asyncio.sleep(300)
                            continue

                        logger.warning(
                            f"MTProto session not ready or login required. Status: {manager.connection_status}. "
                            f"Waiting {retry_delay}s before retry..."
                        )
                        if manager.connection_status == "AUTH_REQUIRED":
                            await send_mtproto_status_alert(
                                "AUTH_REQUIRED",
                                "Telegram sessiyasi bekor qilingan yoki 2FA talab qilinmoqda. connect_mtproto.py orqali qayta ulang."
                            )
                        elif manager.connection_status == "ERROR":
                            await send_mtproto_status_alert(
                                "ERROR",
                                f"MTProto ulanish xatoligi: {(manager.last_error or '')[:120]}"
                            )
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)
                        continue

                    logger.info("MTProto successfully CONNECTED! Listening for Humocardbot messages...")
                    retry_delay = 5
                    acc_user = manager.account_info.get("username") or manager.phone_number or ""
                    await send_mtproto_status_alert(
                        "CONNECTED",
                        f"Akkaunt (@{acc_user}) muvaffaqiyatli ulandi! Humocardbot xabarnomalari 24/7 rejimda tinglanmoqda."
                    )
                    if manager.client:
                        await manager.client.run_until_disconnected()
                    manager.connection_status = "DISCONNECTED"
                    manager._sync_status_to_db("DISCONNECTED", "MTProto client disconnected")
                    logger.warning("MTProto client disconnected. Reconnecting in 5s...")
                    await send_mtproto_status_alert(
                        "DISCONNECTED",
                        "MTProto mijoz aloqasi uzildi. Server 5 soniyada avtomatik qayta ulanishga urinmoqda..."
                    )
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"MTProto worker loop exception: {e}. Retrying in {retry_delay}s...")
                    await send_mtproto_status_alert(
                        "ERROR",
                        f"MTProto xatoligi: {str(e)[:120]}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)

        mtproto_task = asyncio.create_task(mtproto_worker_loop())

        # 5. Start Telegram Bot polling in background (if enabled and configured)
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        enable_bot_polling = os.getenv("ENABLE_BOT_POLLING", "true").lower() in ("true", "1", "yes")
        if bot_token and not bot_token.startswith("your_") and enable_bot_polling:
            async def bot_worker_loop():
                global _bot_instance, _dp_instance
                try:
                    from src.bot.bot import create_bot_app, setup_bot_commands
                    bot, dp, _, _ = create_bot_app()
                    _bot_instance = bot
                    _dp_instance = dp
                    await bot.delete_webhook(drop_pending_updates=True)
                    await setup_bot_commands(bot)
                    me = await bot.get_me()
                    logger.info(f"Telegram Bot @{me.username} polling started successfully in All-in-One server.")
                    await dp.start_polling(bot)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Telegram Bot polling error: {e}")

            bot_task = asyncio.create_task(bot_worker_loop())
        # 6. Anti-sleep keep-alive pinger for Render cloud deployment
        async def keepalive_pinger_loop():
            target_url = os.getenv("WEB_APP_URL", "https://rully-app.onrender.com").rstrip("/") + "/api/health"
            await asyncio.sleep(60)  # Grace period on startup
            import httpx
            while True:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        r = await client.get(target_url)
                        logger.debug(f"Render keepalive ping: {r.status_code}")
                except Exception as e:
                    logger.debug(f"Render keepalive notice: {e}")
                await asyncio.sleep(420)  # Every 7 minutes (Render idle limit is 15 minutes)

        keepalive_task = asyncio.create_task(keepalive_pinger_loop())
    else:
        logger.info("Running in Vercel Serverless environment. Long-running daemons disabled.")

    yield

    # Teardown
    if keepalive_task:
        keepalive_task.cancel()
    if bot_task:
        bot_task.cancel()
    if _dp_instance:
        try:
            await _dp_instance.stop_polling()
        except Exception:
            pass
    if _bot_instance:
        try:
            await _bot_instance.session.close()
        except Exception:
            pass
    if mtproto_task:
        mtproto_task.cancel()
    if not IS_VERCEL:
        try:
            manager = get_mtproto_manager()
            if manager.client and manager.client.is_connected():
                await manager.client.disconnect()
        except Exception:
            pass
    if expiration_task:
        expiration_task.cancel()
    if question_sync_task:
        question_sync_task.cancel()


app = FastAPI(
    title="RULLY Avtotest & Admin Financial Gateway API",
    description="REST API for RULLY Telegram Mini App & Admin MTProto Payment Control Center",
    version="2.1.0",
    lifespan=lifespan
)

# Enable GZip compression for responses >= 1000 bytes (boosts Render/cold-start static transfer)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Strict CORS Configuration for Mini App webviews, official Telegram clients, and private admin web access
ALLOWED_ORIGINS = [
    "https://rully-rully4.vercel.app",
    "https://rully-three.vercel.app",
    "https://rully-app.onrender.com",
    "https://web.telegram.org",
    "https://webk.telegram.org",
    "https://webz.telegram.org",
    "https://t.me",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173",
]
_extra_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _extra_origins:
    ALLOWED_ORIGINS.extend(_extra_origins)

_web_app_url = os.getenv("WEB_APP_URL", "").strip()
if _web_app_url and _web_app_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_web_app_url)

# Strict Regex: only trusted rully domains, official telegram origins, and localhost ports
STRICT_CORS_ORIGIN_REGEX = r"^https?:\/\/(localhost|127\.0\.0\.1|rully[a-zA-Z0-9-]*\.vercel\.app|rully[a-zA-Z0-9-]*\.onrender\.com|web[kz]?\.telegram\.org|t\.me)(:[0-9]+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=STRICT_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in ("/", "/index.html", "/admin", "/admin/", "/static/index.html", "/static/admin/index.html"):
        response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    elif path.startswith(("/static/css/", "/static/js/", "/static/img/", "/static/images/")):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == "/api/categories":
        response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400"
    elif path.startswith("/api/amaliy/"):
        response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
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
@app.get("/healthz")
@app.get("/api/ping")
async def health_check():
    from src.mtproto.service import get_mtproto_manager
    mtproto = get_mtproto_manager()
    return {
        "status": "healthy",
        "pong": True,
        "service": "rully-miniapp-api",
        "version": "2.1.0",
        "environment": "vercel" if IS_VERCEL else "standalone-cloud",
        "canonical_db": "master_database.sqlite",
        "turso_configured": bool(os.getenv("TURSO_DATABASE_URL")),
        "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "gemini_key_len": len((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "")),
        "mtproto_status": mtproto.connection_status,
        "bot_active": _bot_instance is not None
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
