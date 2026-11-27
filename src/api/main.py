"""
RULLY Avtotest Telegram Mini App & Admin Financial Control Center - FastAPI Main Application.
"""

import asyncio
import logging
import os
import threading
import time as _time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# User-facing Mini App Routers (always eagerly mounted for fast serverless boot)
from src.api.routes_auth import router as auth_router
from src.api.routes_theory import router as theory_router
from src.api.routes_practical import router as practical_router
from src.api.routes_payment import router as payment_router
from src.api.routes_telegram import router as telegram_router
from src.api.routes_ai import router as ai_router
from src.security.observability import observability

logger = logging.getLogger(__name__)

_ADMIN_MOUNT_LOCK = threading.Lock()

# CSP directives split cleanly: Admin UI relies on inline handlers and is strictly non-frameable;
# User Mini App forbids unsafe-inline scripts and permits official Telegram Web iFrame hosts.
_CSP_USER_MINIAPP = (
    "default-src 'self'; "
    "script-src 'self' https://telegram.org; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https://cdn.jsdelivr.net https://raw.githubusercontent.com https://t.me https://*.telegram.org; "
    "connect-src 'self' https://rully-three.vercel.app https://rully-app.onrender.com https://cdn.jsdelivr.net; "
    "frame-ancestors 'self' https://web.telegram.org https://webk.telegram.org https://webz.telegram.org https://t.me; "
    "base-uri 'self'; form-action 'self'; object-src 'none'"
)
_CSP_ADMIN_PANEL = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https://cdn.jsdelivr.net https://raw.githubusercontent.com; "
    "connect-src 'self' https://rully-three.vercel.app https://rully-app.onrender.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'; object-src 'none'"
)


def _attach_admin_routers(target_app: FastAPI) -> None:
    """Imports and registers the 12 Admin routers cleanly (deferred on serverless cold starts)."""
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

    for r in (
        admin_auth_router,
        admin_dashboard_router,
        admin_users_router,
        admin_plans_router,
        admin_cards_router,
        admin_orders_router,
        admin_payments_router,
        admin_mtproto_router,
        admin_analytics_router,
        admin_logs_router,
        admin_broadcast_router,
        admin_questions_router,
    ):
        target_app.include_router(r)

# Background worker for order expiration
async def order_expiration_worker():
    """Runs periodically (every 15 minutes) to expire stale payment orders without blocking the event loop."""
    from src.payments.order_manager import expire_stale_orders
    while True:
        try:
            expired_count = await asyncio.to_thread(expire_stale_orders)
            if expired_count > 0:
                logger.info(f"Order expiration worker: Expired {expired_count} stale orders.")
        except Exception as e:
            logger.error(f"Error in order expiration worker: {e}")
        await asyncio.sleep(900)


async def periodic_question_sync_worker():
    """
    Periodically checks external theory sources for new questions every 12 hours in a worker thread.
    Respects ENABLE_INTERNAL_QUESTION_SYNC=false when offloaded to external GitHub Actions cron (Decision U-03).
    """
    await asyncio.sleep(60)  # Initial grace delay after startup
    while True:
        try:
            from src.sync.service import QuestionSyncService

            def _sync_once():
                svc = QuestionSyncService()
                return svc.check_for_updates(auto_stage=True)

            check_res = await asyncio.to_thread(_sync_once)
            if check_res.get("has_updates"):
                logger.info(f"Periodic question sync worker: Staged {check_res.get('newly_staged_count', 0)} items for admin review.")
        except Exception as e:
            logger.error(f"Error in periodic question sync worker (isolated from MTProto/Bot): {e}")
        await asyncio.sleep(43200)  # 12 hours


IS_VERCEL = bool(os.getenv("VERCEL"))
_bot_instance = None
_dp_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_instance, _dp_instance
    is_vercel_runtime = bool(IS_VERCEL or os.getenv("VERCEL"))

    # 1. Run migrations and database schema updates only on local/standalone servers
    if not is_vercel_runtime:
        try:
            from src.database_migrations import run_migrations
            from src.admin.auth_service import ensure_admin_user_exists
            run_migrations()
            ensure_admin_user_exists()
        except Exception as e:
            logger.error(f"Startup migration error: {e}")

    expiration_task = None
    question_sync_task = None
    mtproto_task = None
    bot_task = None
    keepalive_task = None

    if not is_vercel_runtime:
        # 2. Start background order expiration task
        expiration_task = asyncio.create_task(order_expiration_worker())

        # 3. Start periodic question sync worker unless offloaded to GitHub Actions (U-03)
        if os.getenv("ENABLE_INTERNAL_QUESTION_SYNC", "true").lower() in ("true", "1", "yes"):
            question_sync_task = asyncio.create_task(periodic_question_sync_worker())
        else:
            logger.info("Internal 12h question sync disabled (offloaded to scheduled webhook/GitHub Actions).")

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
    if not is_vercel_runtime:
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


_is_cloud_prod = (
    os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod", "standalone-cloud")
    or bool(os.getenv("VERCEL"))
    or bool(os.getenv("RENDER"))
)

# Strict CORS Configuration for Mini App webviews, official Telegram clients, and private admin web access
ALLOWED_ORIGINS = [
    "https://rully-rully4.vercel.app",
    "https://rully-three.vercel.app",
    "https://rully-app.onrender.com",
    "https://web.telegram.org",
    "https://webk.telegram.org",
    "https://webz.telegram.org",
    "https://t.me",
]
if not _is_cloud_prod:
    ALLOWED_ORIGINS.extend([
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ])
_extra_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _extra_origins:
    ALLOWED_ORIGINS.extend(_extra_origins)

_web_app_url = os.getenv("WEB_APP_URL", "").strip()
if _web_app_url and _web_app_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_web_app_url)

for _deploy_host in (os.getenv("VERCEL_URL", "").strip(), os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()):
    if _deploy_host:
        _deploy_origin = _deploy_host if _deploy_host.startswith("http") else f"https://{_deploy_host}"
        if _deploy_origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(_deploy_origin)

STRICT_CORS_ORIGIN_REGEX = None if _is_cloud_prod else r"^https?:\/\/(localhost|127\.0\.0\.1)(:[0-9]+)?$"


def create_app(public_only: Optional[bool] = None) -> FastAPI:
    """
    Application factory enabling Vercel public-router cold-start splitting (`public_only=True`)
    while loading full user + admin + worker capability on standalone Render servers (`public_only=False`).
    """
    t_boot = _time.perf_counter()
    use_public_split = (
        bool(public_only)
        if public_only is not None
        else bool(IS_VERCEL or os.getenv("RULLY_PUBLIC_ONLY", "").lower() in ("1", "true", "yes"))
    )
    disable_admin_on_split = os.getenv("VERCEL_DISABLE_ADMIN", "").lower() in ("1", "true", "yes")

    application = FastAPI(
        title="RULLY Avtotest & Admin Financial Gateway API",
        description="REST API for RULLY Telegram Mini App & Admin MTProto Payment Control Center",
        version="2.1.0",
        lifespan=lifespan,
    )
    application.state.public_only = use_public_split
    application.state.admin_routers_loaded = not use_public_split

    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=STRICT_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )

    @application.exception_handler(Exception)
    async def sanitized_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", uuid.uuid4().hex[:12])
        logger.exception(f"Unhandled exception [req_id={req_id}] on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "Internal server error", "request_id": req_id},
            headers={"X-Request-ID": req_id},
        )

    @application.middleware("http")
    async def security_and_observability_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        req_id = str(req_id)[:32]
        request.state.request_id = req_id
        t0 = _time.perf_counter()
        path = request.url.path

        # Lazy admin router loading or explicit 503 block on public-split cold-start apps
        if path.startswith("/api/admin"):
            if use_public_split and disable_admin_on_split:
                response = JSONResponse(
                    status_code=503,
                    content={
                        "ok": False,
                        "detail": "Admin endpoints are served via standalone Render host.",
                        "request_id": req_id,
                    },
                )
            else:
                if not application.state.admin_routers_loaded:
                    with _ADMIN_MOUNT_LOCK:
                        if not application.state.admin_routers_loaded:
                            _attach_admin_routers(application)
                            application.state.admin_routers_loaded = True
                response = await call_next(request)
        else:
            response = await call_next(request)

        elapsed_ms = round((_time.perf_counter() - t0) * 1000.0, 2)
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        is_admin_surface = path.startswith(("/admin", "/static/admin/"))
        response.headers["Content-Security-Policy"] = _CSP_ADMIN_PANEL if is_admin_surface else _CSP_USER_MINIAPP
        if is_admin_surface:
            response.headers["X-Frame-Options"] = "DENY"

        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").lower()
        if request.url.scheme == "https" or forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if path in ("/", "/index.html", "/admin", "/admin/", "/static/index.html", "/static/admin/index.html"):
            response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        elif path.startswith(("/static/css/", "/static/js/", "/static/img/", "/static/images/")):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path == "/api/categories":
            response.headers["Cache-Control"] = "private, no-store"
        elif path.startswith("/api/amaliy/"):
            response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"

        observability.record_request(
            method=request.method,
            path=path,
            status_code=getattr(response, "status_code", 200),
            duration_ms=elapsed_ms,
            request_id=req_id,
        )
        return response

    # Include User Mini App API Routers
    for user_router in (
        auth_router,
        theory_router,
        practical_router,
        payment_router,
        telegram_router,
        ai_router,
    ):
        application.include_router(user_router)

    # Full-mode hosts (Render/Local) eagerly register Admin routers
    if not use_public_split:
        _attach_admin_routers(application)

    # Serve & Proxy Images with Local + Remote Fallback & Edge Caching
    images_dir = os.path.abspath("data/images/original")

    @application.get("/images/{filename}")
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

    static_dir = os.path.abspath("static")
    if os.path.exists(static_dir):
        application.mount("/static", StaticFiles(directory=static_dir), name="static")

    @application.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)

    @application.get("/api/health")
    @application.get("/healthz")
    @application.get("/api/ping")
    async def health_check():
        mtproto_status = "serverless-disabled"
        if not IS_VERCEL:
            try:
                from src.mtproto.service import get_mtproto_manager
                mtproto_status = get_mtproto_manager().connection_status
            except ImportError:
                pass
        return {
            "status": "healthy",
            "pong": True,
            "service": "rully-miniapp-api",
            "version": "2.1.0",
            "platform_version": "2.0.0",
            "environment": "vercel" if IS_VERCEL else "standalone-cloud",
            "router_mode": "public-split" if use_public_split else "full",
            "admin_routers_loaded": bool(application.state.admin_routers_loaded),
            "observability_ready": True,
            "canonical_db": "master_database.sqlite",
            "turso_configured": bool(os.getenv("TURSO_DATABASE_URL")),
            "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "mtproto_status": mtproto_status,
            "bot_active": _bot_instance is not None
        }

    @application.get("/admin")
    @application.get("/admin/")
    async def serve_admin_panel():
        admin_index = os.path.join(static_dir, "admin", "index.html")
        if os.path.exists(admin_index):
            return FileResponse(admin_index)
        return {"error": "Admin panel template not found"}

    @application.get("/")
    async def serve_index():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "RULLY Mini App API is running."}

    cold_start_ms = round((_time.perf_counter() - t_boot) * 1000.0, 2)
    observability.set_boot_metadata("public-split" if use_public_split else "full", cold_start_ms)
    return application


app = create_app()
