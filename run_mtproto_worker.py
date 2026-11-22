"""
RULLY Standalone MTProto Humocardbot Daemon Worker.
Runs 24/7 as an independent background service to capture payment notifications,
auto-match orders, and activate subscriptions directly on Turso Cloud Database.
"""

import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.mtproto.service import get_mtproto_manager
from src.payments.order_manager import expire_stale_orders
from src.security.telegram_notifier import send_mtproto_status_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mtproto_worker")

async def order_expiration_loop():
    """Periodically marks expired orders as EXPIRED in the cloud database."""
    while True:
        try:
            expired_count = expire_stale_orders()
            if expired_count > 0:
                logger.info(f"Expired {expired_count} stale orders in cloud database.")
        except Exception as e:
            logger.error(f"Error in order expiration loop: {e}")
        await asyncio.sleep(60)

async def main():
    logger.info("Starting RULLY 24/7 MTProto Payment Worker...")
    manager = get_mtproto_manager()

    # Start background order expiration
    asyncio.create_task(order_expiration_loop())

    # Start MTProto Telethon client with automatic retry
    retry_delay = 5
    while True:
        try:
            logger.info("Initializing and connecting MTProto client from stored session...")
            connected = await manager.initialize_and_start()
            if not connected:
                logger.warning(
                    f"No active authorized session found or login required. Status: {manager.connection_status}. "
                    f"Waiting {retry_delay}s before retry... (Connect via Admin Panel if not connected)"
                )
                if manager.connection_status == "AUTH_REQUIRED":
                    await send_mtproto_status_alert(
                        "AUTH_REQUIRED",
                        "Telegram sessiyasi bekor qilingan yoki muddati tugagan. connect_mtproto.py orqali qayta ulang."
                    )
                await asyncio.sleep(retry_delay)
                continue

            logger.info("MTProto successfully CONNECTED! Listening for Humocardbot messages...")
            retry_delay = 5  # reset delay on success
            acc_user = manager.account_info.get("username") or manager.phone_number or ""
            await send_mtproto_status_alert(
                "CONNECTED",
                f"Akkaunt (@{acc_user}) muvaffaqiyatli ulandi! Humocardbot xabarnomalari 24/7 rejimda tinglanmoqda."
            )
            await manager.client.run_until_disconnected()
            logger.warning("MTProto client disconnected. Reconnecting in 5s...")
            await send_mtproto_status_alert(
                "DISCONNECTED",
                "MTProto mijoz aloqasi uzildi. Server 5 soniyada avtomatik qayta ulanishga urinmoqda..."
            )
            await asyncio.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Worker stopped by user.")
            break
        except Exception as e:
            logger.error(f"MTProto worker exception: {e}. Retrying in {retry_delay}s...")
            await send_mtproto_status_alert(
                "ERROR",
                f"MTProto worker xatoligi: {str(e)[:120]}"
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
